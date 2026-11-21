"""Silver building blocks (each is called by one pipeline step; see pipelines/*/silver/*/NN_*.py):
read_bronze_increment -> apply_canonical_mapping -> deduplicate -> apply_lookups -> run_dq -> add_silver_meta -> merge_to_silver."""
from pyspark.sql import Window
from pyspark.sql import functions as F

from edap_framework.dq.engine import apply_rule_set, load_rule_set
from edap_framework.dq.quarantine import exclude_quarantined
from edap_framework.metadata import watermarks
from edap_framework.silver import transforms

BRONZE_LINEAGE = {"_bronze_file": "_source_file", "_bronze_batch_id": "_batch_id", "_landing_batch_id": "_landing_batch_id",
                  "_bronze_row_hash": "_row_hash", "_bronze_ingest_ts": "_ingest_ts", "_source_system": "_source_system",
                  "_source_object": "_source_object"}


def wm_key(mapping, ac_prefix):
    return "SILVER.%s_%s" % (ac_prefix, mapping["entity"])


def read_bronze_increment(spark, mapping, env, ac_prefix, adhoc=False, from_ts=None):
    """New Bronze rows since the Silver watermark (Adhoc: since from_ts, or everything), minus DQ-quarantined rows."""
    src = mapping["source"]
    store = "%s.metadata.watermarks" % env["catalog"]
    last = from_ts if adhoc else watermarks.get_watermark(spark, store, wm_key(mapping, ac_prefix))
    df = spark.table(src["bronze_table"])
    if last is not None:
        df = df.where(F.col("_ingest_ts") > F.lit(last))
    if src.get("where"):
        df = df.where(src["where"])
    if src.get("exclude_quarantined", True):
        df = exclude_quarantined(spark, df, env, src["bronze_table"])
    if src.get("transform"):
        df = transforms.REGISTRY[src["transform"]](df)
    return df, df.agg(F.max("_ingest_ts")).collect()[0][0]


def apply_canonical_mapping(df, mapping):
    cols = [F.expr(e).alias(c) for c, e in mapping["columns"].items()]
    lin = [F.col(b).alias(a) for a, b in BRONZE_LINEAGE.items() if b in df.columns]
    return df.select(*cols, *lin)


def deduplicate(df, mapping):
    d = mapping["dedup"]
    w = Window.partitionBy(*d["partition_by"]).orderBy(*[F.expr(o) for o in d["order_by"]])
    return df.withColumn("_rn", F.row_number().over(w)).where("_rn = 1").drop("_rn")


def _lookup(spark, df, lk):
    ref = spark.table(lk["table"])
    if lk.get("active_only"):
        ref = ref.where("active_flag")
    on = lk["on"]
    if "flag" in lk:
        ref = ref.select(*[F.col(rc).alias("_k_%s" % rc) for rc in on.values()]).distinct().withColumn(lk["flag"], F.lit(True))
        out = df.join(F.broadcast(ref), [df[dc] == ref["_k_%s" % rc] for dc, rc in on.items()], "left")
        return out.withColumn(lk["flag"], F.coalesce(F.col(lk["flag"]), F.lit(False))).drop(*["_k_%s" % rc for rc in on.values()])
    sel = [F.col(rc).alias("_k_%s" % rc) for rc in on.values()] + [F.col(rc).alias(nc) for nc, rc in lk["add"].items()]
    ref = ref.select(*sel).dropDuplicates(["_k_%s" % rc for rc in on.values()])
    return df.join(F.broadcast(ref), [df[dc] == ref["_k_%s" % rc] for dc, rc in on.items()], "left").drop(*["_k_%s" % rc for rc in on.values()])


def apply_lookups(spark, df, mapping):
    for lk in mapping.get("lookups", []):
        df = _lookup(spark, df, lk)
    return df


def run_dq(spark, df, mapping, env, batch_id, fq, rules_vars):
    """DQX business rules; invalid rows go to quarantine.silver_invalid. Returns (valid_df without helper columns, stats)."""
    n = df.count()
    valid, stats = df, {"total": n, "quarantined": 0, "warned": 0}
    if mapping.get("dq", {}).get("rules_file"):
        valid, stats = apply_rule_set(spark, df, load_rule_set(mapping["dq"]["rules_file"], rules_vars), env, batch_id, table_name=fq)
    return valid.drop(*[c for c in valid.columns if c.startswith("_ref_")]), stats


def add_silver_meta(df, mapping, batch_id, run_id, spec_path):
    return (df.withColumn("_silver_batch_id", F.lit(batch_id)).withColumn("_run_id", F.lit(run_id))
              .withColumn("_spec_path", F.lit(spec_path)).withColumn("_spec_version", F.lit(str(mapping.get("version", 1))))
              .withColumn("_silver_updated_ts", F.current_timestamp()))


def merge_to_silver(spark, df, mapping, fq):
    """MERGE on the business key; update_when keeps an older late arrival from overwriting newer data."""
    spark.sql("CREATE SCHEMA IF NOT EXISTS %s" % ".".join(fq.split(".")[:2]))
    if not spark.catalog.tableExists(fq):
        df.limit(0).write.saveAsTable(fq)
    view = "_silver_src_%s" % fq.replace(".", "_")
    df.createOrReplaceTempView(view)
    m = mapping["merge"]
    on = " AND ".join("t.%s = s.%s" % (k, k) for k in m["keys"])
    matched = ("WHEN MATCHED AND (%s) THEN UPDATE SET *" % m["update_when"]) if m.get("update_when") else ""
    spark.sql("MERGE INTO %s t USING %s s ON %s %s WHEN NOT MATCHED THEN INSERT *" % (fq, view, on, matched))


def advance_watermark(spark, env, mapping, ac_prefix, hi, batch_id, adhoc=False):
    """Routine advances the Silver watermark; an Adhoc rebuild must not move it backwards (advance only forward)."""
    store, key = "%s.metadata.watermarks" % env["catalog"], wm_key(mapping, ac_prefix)
    cur = watermarks.get_watermark(spark, store, key)
    if hi is not None and (cur is None or hi > cur):
        watermarks.set_watermark(spark, store, key, hi, batch_id)


def apply_governance(spark, fq, mapping, spec_path, asset_class):
    g, esc = mapping["governance"], (lambda s: str(s).replace("'", "''"))
    spark.sql("COMMENT ON TABLE %s IS '%s'" % (fq, esc("%s [%s]" % (g["description"], asset_class))))
    tags = {"layer": "silver", "asset_class": asset_class, "entity": mapping["entity"], "owner": g["owner"], "sensitivity": g["sensitivity"], "spec": spec_path}
    spark.sql("ALTER TABLE %s SET TAGS (%s)" % (fq, ", ".join("'%s' = '%s'" % (k, esc(v)) for k, v in tags.items())))
