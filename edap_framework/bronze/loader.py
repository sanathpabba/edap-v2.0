"""Bronze building blocks (each is called by one pipeline step; see pipelines/*/bronze/*/NN_*.py).
read_landing -> shape_columns -> route_to_asset_class -> add_meta_properties -> write_bronze -> apply_governance.
Bronze is the raw, replayable record: no cleansing, no dedup. Lineage columns on every row:
  _source_system, _source_object, _source_file, _landing_batch_id, _batch_id, _run_id, _row_hash, _spec_path, _spec_version,
  _ingest_ts, _ingest_date."""
from pyspark.sql import functions as F

from edap_framework.core import config, spark_utils

INSTRUMENT_MASTER = "edap.bronze.common_sql_instruments"


def _ddl(columns):
    return ", ".join("%s %s" % (c, t) for c, t in columns.items())


def read_landing(spark, spec, env, adhoc=False, from_ts=None, to_ts=None):
    """Routine: Auto Loader stream (availableNow, incremental by file). Adhoc: batch read of landing files, optionally a time window."""
    inp = spec["input"]
    schema = inp.get("schema") or ({} if inp["format"] == "text" else spec.get("columns"))
    path = config.storage_uri(env, inp["container"], inp["path"])
    if not adhoc:
        r = spark.readStream.format("cloudFiles").option("cloudFiles.format", inp["format"]).option("cloudFiles.useNotifications", "false")
    else:
        r = spark.read.format(inp["format"])
    for k, v in (inp.get("options") or {}).items():
        r = r.option(k, v)
    if schema:
        r = r.schema(_ddl(schema))
    df = r.load(path)
    if adhoc and from_ts:
        df = df.where(F.col("_metadata.file_modification_time") >= F.lit(from_ts))
    if adhoc and to_ts:
        df = df.where(F.col("_metadata.file_modification_time") <= F.lit(to_ts))
    return df


def shape_columns(df, spec):
    """Spec-driven shaping: json_extract (whole-text envelope) / parse (raw payload + permissive typed parse) / extra_columns."""
    df = df.withColumn("_src_path", F.col("_metadata.file_path"))
    if spec.get("json_extract"):
        df = df.select("_src_path", *[F.get_json_object("value", p).alias(c) for c, p in spec["json_extract"].items()])
    if spec.get("parse"):
        p = spec["parse"]
        df = df.withColumn(spec["raw_column"], F.col(p["from"])) \
               .withColumn("_parsed", F.from_json(F.col(p["from"]), _ddl(p["columns"]), {"mode": "PERMISSIVE"}))
        for c in p["columns"]:
            df = df.withColumn(c, F.col("_parsed.%s" % c))
        for out, src in (spec.get("transport_columns") or {}).items():
            df = df.withColumn(out, F.col(src))
        df = df.drop("_parsed", "key", "value", "topic", "partition", "offset", "timestamp")
    for c, expr in (spec.get("extra_columns") or {}).items():
        df = df.withColumn(c, F.expr(expr.replace("_source_file", "_src_path")))
    return df


def route_to_asset_class(spark, df, spec, ac):
    """Keep only the rows of this pipeline's asset class (by the row's instrument, via the shared instrument master).
    Rows whose instrument no asset class knows go to the pipeline flagged receives_unresolved, so DQ can quarantine them."""
    scope = spec.get("scope") or {"by": "none"}
    if scope["by"] != "instrument":
        return df
    key = lambda c: F.upper(F.trim(F.col(c)))
    master = spark.table(INSTRUMENT_MASTER)
    mine = master.where(key("sec_type").isin(ac.sec_types)).select(key("sec_code").alias("_mk")).distinct().withColumn("_mine", F.lit(True))
    known = master.select(key("sec_code").alias("_ak")).distinct().withColumn("_known", F.lit(True))
    out = df.withColumn("_route_key", key(scope["column"]))
    out = out.join(F.broadcast(mine), out["_route_key"] == mine["_mk"], "left").join(F.broadcast(known), out["_route_key"] == known["_ak"], "left")
    keep = F.col("_mine").isNotNull() | (F.lit(ac.receives_unresolved) & F.col("_known").isNull())
    return out.where(keep).drop("_route_key", "_mk", "_mine", "_ak", "_known")


def _hash_columns(spec):
    if spec.get("raw_column"):
        return [spec["raw_column"]]
    if spec.get("json_extract"):
        return list(spec["json_extract"])
    return list(spec["columns"])


def add_meta_properties(spark, df, spec, batch_id, spec_path, run_id):
    """Audit + lineage columns (landing batch, row hash, run id, spec path/version, ingest time)."""
    lin = spec["lineage"]
    if lin["landing_batch"].startswith("path"):
        df = df.withColumn("_landing_batch_id", F.regexp_extract("_src_path", r"batch_id=([^/]+)", 1))
    else:
        reg = spark.table("edap.audit.file_arrivals").select(F.col("file_path").alias("_reg_path"), F.col("batch_id").alias("_landing_batch_id")) \
                   .dropDuplicates(["_reg_path"])
        df = df.join(F.broadcast(reg), df["_src_path"] == reg["_reg_path"], "left").drop("_reg_path")
    if lin.get("row_hash") == "sha256":
        df = df.withColumn("_row_hash", F.sha2(F.concat_ws("||", *[F.coalesce(F.col(c).cast("string"), F.lit("")) for c in _hash_columns(spec)]), 256))
    a = spec["audit_columns"]
    return (df.withColumn("_source_system", F.lit(a["_source_system"])).withColumn("_source_object", F.lit(a["_source_object"]))
              .withColumn("_batch_id", F.lit(batch_id)).withColumn("_run_id", F.lit(run_id))
              .withColumn("_spec_path", F.lit(spec_path)).withColumn("_spec_version", F.lit(str(spec.get("version", 1))))
              .withColumn("_ingest_ts", F.current_timestamp()).withColumn("_ingest_date", F.current_date())
              .withColumn("_source_file", F.col("_src_path")).drop("_src_path"))


def write_bronze(spark, df, spec, env, batch_id, adhoc=False):
    """Routine: streaming append (availableNow) with a checkpoint. Adhoc: replay - delete the rows of the landing batches being
    replayed, then append, so a replay never duplicates."""
    tgt = spec["target"]
    fq = spark_utils.fq_table(tgt)
    spark.sql("CREATE SCHEMA IF NOT EXISTS %s.%s" % (tgt["catalog"], tgt["schema"]))
    if adhoc:
        batches = [r[0] for r in df.select("_landing_batch_id").distinct().collect() if r[0]]
        if batches and spark.catalog.tableExists(fq):
            spark.sql("DELETE FROM %s WHERE _landing_batch_id IN (%s)" % (fq, ",".join("'%s'" % b for b in batches)))
        w = df.write.mode("append")
        if tgt.get("partition_by"):
            w = w.partitionBy(*tgt["partition_by"])
        w.saveAsTable(fq)
    else:
        cp = config.storage_uri(env, spec["checkpoint"]["container"], spec["checkpoint"]["path"])
        w = df.writeStream.option("checkpointLocation", cp).trigger(availableNow=True)
        if tgt.get("partition_by"):
            w = w.partitionBy(*tgt["partition_by"])
        w.toTable(fq).awaitTermination()
    return spark.table(fq).where(F.col("_batch_id") == batch_id).count()


def apply_governance(spark, spec, spec_path, asset_class):
    """Unity Catalog table comment + tags from the spec's governance block."""
    fq, g = spark_utils.fq_table(spec["target"]), spec["governance"]
    esc = lambda s: str(s).replace("'", "''")
    for k, v in (spec["target"].get("properties") or {}).items():
        spark.sql("ALTER TABLE %s SET TBLPROPERTIES ('%s' = '%s')" % (fq, k, v))
    spark.sql("COMMENT ON TABLE %s IS '%s'" % (fq, esc("%s [%s]" % (g["description"], asset_class))))
    tags = {"layer": "bronze", "asset_class": asset_class, "source_system": spec["source_system"], "owner": g["owner"],
            "sensitivity": g["sensitivity"], "spec": spec_path}
    spark.sql("ALTER TABLE %s SET TAGS (%s)" % (fq, ", ".join("'%s' = '%s'" % (k, esc(v)) for k, v in tags.items())))
