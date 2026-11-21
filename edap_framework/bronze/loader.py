"""Generic Bronze loader. One call = one table spec (definitions/bronze/<source>/<table>.yml).
Reads landing files incrementally with Auto Loader (availableNow), adds audit + lineage columns, appends to a Delta table.
No cleansing, no dedup: Bronze is the raw, replayable record.

Lineage columns on every Bronze row:
  _source_system, _source_object   where the data came from
  _source_file                     exact landing file
  _landing_batch_id                batch that wrote the landing file (path for SQL/events, file registry for files/FX)
  _batch_id, _run_id               this Bronze batch, and the Databricks job run that executed it
  _row_hash                        sha256 over the source columns
  _spec_path, _spec_version        the YAML (and version) that produced the row
  _ingest_ts, _ingest_date         when it was loaded
Unity Catalog lineage (table/column) comes from the platform; the table also gets a comment and tags from the spec."""
import datetime as dt

from pyspark.sql import functions as F

from edap_framework.core import audit, config, spark_utils


def _ddl(columns):
    return ", ".join("%s %s" % (c, t) for c, t in columns.items())


def _read(spark, spec, env):
    inp = spec["input"]
    r = (spark.readStream.format("cloudFiles").option("cloudFiles.format", inp["format"])
         .option("cloudFiles.useNotifications", "false"))
    for k, v in (inp.get("options") or {}).items():
        r = r.option(k, v)
    schema = inp.get("schema") or ({} if inp["format"] == "text" else spec.get("columns"))
    if schema:
        r = r.schema(_ddl(schema))
    return r.load(config.storage_uri(env, inp["container"], inp["path"]))


def _hash_columns(spec):
    if spec.get("raw_column"):                                     # events: the untouched payload
        return [spec["raw_column"]]
    if spec.get("json_extract"):                                   # FX: the envelope fields
        return list(spec["json_extract"])
    return list(spec["columns"])                                   # SQL / files


def _shape(spark, df, spec, batch_id, spec_path):
    """Spec-driven column shaping: json_extract / parse / extra_columns / hash / audit + lineage columns."""
    df = df.withColumn("_src_path", F.col("_metadata.file_path"))
    if spec.get("json_extract"):                                   # whole-text JSON envelope (REST API)
        df = df.select("_src_path", *[F.get_json_object("value", p).alias(c) for c, p in spec["json_extract"].items()])
    if spec.get("parse"):                                          # raw payload + permissive typed parse (events)
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

    lin = spec["lineage"]
    # landing batch: from the folder name, or looked up in the landing file registry (stream-static join)
    if lin["landing_batch"].startswith("path"):
        df = df.withColumn("_landing_batch_id", F.regexp_extract("_src_path", r"batch_id=([^/]+)", 1))
    else:
        reg = spark.table("edap.audit.file_arrivals").select(F.col("file_path").alias("_reg_path"), F.col("batch_id").alias("_landing_batch_id")) \
                   .dropDuplicates(["_reg_path"])
        df = df.join(F.broadcast(reg), df["_src_path"] == reg["_reg_path"], "left").drop("_reg_path")
    if lin.get("row_hash") == "sha256":
        df = df.withColumn("_row_hash", F.sha2(F.concat_ws("||", *[F.coalesce(F.col(c).cast("string"), F.lit("")) for c in _hash_columns(spec)]), 256))

    a = spec["audit_columns"]
    return (df.withColumn("_source_system", F.lit(a["_source_system"]))
              .withColumn("_source_object", F.lit(a["_source_object"]))
              .withColumn("_batch_id", F.lit(batch_id))
              .withColumn("_run_id", F.lit(audit.run_id()))
              .withColumn("_spec_path", F.lit(spec_path))
              .withColumn("_spec_version", F.lit(str(spec.get("version", 1))))
              .withColumn("_ingest_ts", F.current_timestamp())
              .withColumn("_ingest_date", F.current_date())
              .withColumn("_source_file", F.col("_src_path"))
              .drop("_src_path"))


def _govern(spark, fq, spec, spec_path):
    """Unity Catalog comment + tags from the spec's governance block (so the catalog describes itself)."""
    g = spec["governance"]
    spark.sql("COMMENT ON TABLE %s IS '%s'" % (fq, g["description"].replace("'", "''")))
    tags = {"layer": "bronze", "source_system": spec["source_system"], "owner": g["owner"], "sensitivity": g["sensitivity"],
            "spec": spec_path}
    spark.sql("ALTER TABLE %s SET TAGS (%s)" % (fq, ", ".join("'%s' = '%s'" % kv for kv in tags.items())))


def load_bronze(spark, spec, env, batch_id=None, scenario=None, spec_path=None):
    batch_id = batch_id or audit.new_batch_id()
    spec_path = spec_path or "definitions/bronze/%s.yml" % spec["table"]
    started = dt.datetime.utcnow()
    tgt = spec["target"]
    fq = spark_utils.fq_table(tgt)
    spark.sql("CREATE SCHEMA IF NOT EXISTS %s.%s" % (tgt["catalog"], tgt["schema"]))
    df = _shape(spark, _read(spark, spec, env), spec, batch_id, spec_path)
    cp = config.storage_uri(env, spec["checkpoint"]["container"], spec["checkpoint"]["path"])
    w = df.writeStream.option("checkpointLocation", cp).trigger(availableNow=True)
    if tgt.get("partition_by"):
        w = w.partitionBy(*tgt["partition_by"])
    q = w.toTable(fq)
    q.awaitTermination()
    for k, v in (tgt.get("properties") or {}).items():
        spark.sql("ALTER TABLE %s SET TBLPROPERTIES ('%s' = '%s')" % (fq, k, v))
    _govern(spark, fq, spec, spec_path)
    n = spark.table(fq).where(F.col("_batch_id") == batch_id).count()
    audit.log_run(spark, "edap.audit.ingestion_runs", batch_id=batch_id, layer="bronze", source_system=spec["source_system"],
                  table_name=spec["table"], scenario=scenario, status="SUCCESS", rows_processed=n, started_ts=started,
                  finished_ts=dt.datetime.utcnow(), details="-> %s" % fq)
    return n
