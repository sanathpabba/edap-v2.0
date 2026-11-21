"""Silver mapping engine. One call = one canonical entity (definitions/mappings/<entity>.yml).

  Bronze (new rows since the Silver watermark, minus DQ-quarantined rows)
    -> canonical columns (rename/cast/derive from YAML expressions)
    -> dedup on business key
    -> lookups (reference data, canonical entities; add columns or referential flags)
    -> DQX business rules (invalid rows -> quarantine.silver_invalid)
    -> MERGE into edap.silver.<entity> (older late arrivals never overwrite newer data)
Lineage columns keep the trail back to the exact Bronze row and file."""
import datetime as dt

from pyspark.sql import Window
from pyspark.sql import functions as F

from edap_framework.core import audit, config, spark_utils
from edap_framework.dq.engine import apply_rule_set, load_rule_set
from edap_framework.dq.quarantine import exclude_quarantined
from edap_framework.metadata import watermarks
from edap_framework.silver import transforms

BRONZE_LINEAGE = {"_bronze_file": "_source_file", "_bronze_batch_id": "_batch_id", "_landing_batch_id": "_landing_batch_id",
                  "_bronze_row_hash": "_row_hash", "_bronze_ingest_ts": "_ingest_ts", "_source_system": "_source_system",
                  "_source_object": "_source_object"}


def _lookup(spark, df, lk):
    ref = spark.table(lk["table"])
    if lk.get("active_only"):
        ref = ref.where("active_flag")
    on = lk["on"]                                                  # {df_col: ref_col}
    if "flag" in lk:
        ref = ref.select(*[F.col(rc).alias("_k_%s" % rc) for rc in on.values()]).distinct().withColumn(lk["flag"], F.lit(True))
        cond = [df[dc] == ref["_k_%s" % rc] for dc, rc in on.items()]
        out = df.join(F.broadcast(ref), cond, "left")
        out = out.withColumn(lk["flag"], F.coalesce(F.col(lk["flag"]), F.lit(False)))
        return out.drop(*["_k_%s" % rc for rc in on.values()])
    sel = [F.col(rc).alias("_k_%s" % rc) for rc in on.values()] + [F.col(rc).alias(nc) for nc, rc in lk["add"].items()]
    ref = ref.select(*sel).dropDuplicates(["_k_%s" % rc for rc in on.values()])
    out = df.join(F.broadcast(ref), [df[dc] == ref["_k_%s" % rc] for dc, rc in on.items()], "left")
    return out.drop(*["_k_%s" % rc for rc in on.values()])


def build_entity(spark, mapping, env, batch_id=None, scenario=None, spec_path=None):
    batch_id = batch_id or audit.new_batch_id()
    spec_path = spec_path or "definitions/mappings/%s.yml" % mapping["entity"]
    started = dt.datetime.utcnow()
    tgt, src = mapping["target"], mapping["source"]
    fq = spark_utils.fq_table(tgt)
    spark.sql("CREATE SCHEMA IF NOT EXISTS %s.%s" % (tgt["catalog"], tgt["schema"]))

    # 1. incremental read of Bronze + exclude rows DQ already quarantined
    wm_key, wm_store = "SILVER.%s" % mapping["entity"], "%s.metadata.watermarks" % env["catalog"]
    last = watermarks.get_watermark(spark, wm_store, wm_key)
    df = spark.table(src["bronze_table"])
    if last is not None:
        df = df.where(F.col("_ingest_ts") > F.lit(last))
    if src.get("exclude_quarantined", True):
        df = exclude_quarantined(spark, df, env, src["bronze_table"])
    if src.get("transform"):
        df = transforms.REGISTRY[src["transform"]](df)
    hi = df.agg(F.max("_ingest_ts")).collect()[0][0]
    if hi is None:
        audit.log_run(spark, "%s.audit.ingestion_runs" % env["catalog"], batch_id=batch_id, layer="silver", source_system="EDAP", table_name=mapping["entity"],
                      scenario=scenario, status="NO_NEW_DATA", rows_processed=0, started_ts=started, finished_ts=dt.datetime.utcnow(), details="no new Bronze rows")
        return {"read": 0}

    # 2. canonical columns + lineage
    cols = [F.expr(e).alias(c) for c, e in mapping["columns"].items()]
    lin = [F.col(b).alias(a) for a, b in BRONZE_LINEAGE.items() if b in df.columns]
    df = df.select(*cols, *lin)
    n_read = df.count()

    # 3. dedup on business key (latest wins per the YAML ordering)
    d = mapping["dedup"]
    w = Window.partitionBy(*d["partition_by"]).orderBy(*[F.expr(o) for o in d["order_by"]])
    df = df.withColumn("_rn", F.row_number().over(w)).where("_rn = 1").drop("_rn")

    # 4. lookups: reference data (add columns) and referential flags
    for lk in mapping.get("lookups", []):
        df = _lookup(spark, df, lk)

    # 5. DQX business rules
    valid, stats = df, {"total": n_read, "quarantined": 0, "warned": 0}
    if mapping.get("dq", {}).get("rules_file"):
        valid, stats = apply_rule_set(spark, df, load_rule_set(mapping["dq"]["rules_file"]), env, batch_id, table_name=fq)
    valid = valid.drop(*[c for c in valid.columns if c.startswith("_ref_")])

    # 6. Silver lineage columns, then MERGE
    valid = (valid.withColumn("_silver_batch_id", F.lit(batch_id)).withColumn("_run_id", F.lit(audit.run_id()))
                  .withColumn("_spec_path", F.lit(spec_path)).withColumn("_spec_version", F.lit(str(mapping.get("version", 1))))
                  .withColumn("_silver_updated_ts", F.current_timestamp()))
    keys, m = mapping["merge"]["keys"], mapping["merge"]
    if not spark.catalog.tableExists(fq):
        valid.limit(0).write.saveAsTable(fq)
    valid.createOrReplaceTempView("_silver_src_%s" % mapping["entity"])
    on = " AND ".join("t.%s = s.%s" % (k, k) for k in keys)
    matched = ("WHEN MATCHED AND (%s) THEN UPDATE SET *" % m["update_when"]) if m.get("update_when") else ""
    spark.sql("MERGE INTO %s t USING _silver_src_%s s ON %s %s WHEN NOT MATCHED THEN INSERT *" % (fq, mapping["entity"], on, matched))

    watermarks.set_watermark(spark, wm_store, wm_key, hi, batch_id)
    _govern(spark, fq, mapping, spec_path)
    n_ok = stats["total"] - stats["quarantined"]
    audit.log_run(spark, "%s.audit.ingestion_runs" % env["catalog"], batch_id=batch_id, layer="silver", source_system="EDAP", table_name=mapping["entity"],
                  scenario=scenario, status="SUCCESS", rows_processed=n_ok, started_ts=started, finished_ts=dt.datetime.utcnow(),
                  details="read %d, quarantined %d, merged %d -> %s" % (n_read, stats["quarantined"], n_ok, fq))
    return {"read": n_read, "quarantined": stats["quarantined"], "merged": n_ok}


def _govern(spark, fq, mapping, spec_path):
    g = mapping["governance"]
    spark.sql("COMMENT ON TABLE %s IS '%s'" % (fq, g["description"].replace("'", "''")))
    tags = {"layer": "silver", "entity": mapping["entity"], "owner": g["owner"], "sensitivity": g["sensitivity"], "spec": spec_path}
    spark.sql("ALTER TABLE %s SET TAGS (%s)" % (fq, ", ".join("'%s' = '%s'" % kv for kv in tags.items())))
