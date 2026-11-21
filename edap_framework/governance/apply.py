"""Governance as code (Phase 14): ownership/tags, grants, column masks and lineage reporting, all driven by definitions/governance/*.yml."""
from pyspark.sql import functions as F

from edap_framework.core import config

esc = lambda s: str(s).replace("'", "''")


def apply_ownership(spark):
    o = config.load_yaml("definitions/governance/ownership.yml")
    c = o["catalog"]
    spark.sql("COMMENT ON CATALOG %s IS '%s'" % (c["name"], esc(c["comment"])))
    spark.sql("ALTER CATALOG %s SET TAGS (%s)" % (c["name"], ", ".join("'%s' = '%s'" % kv for kv in c["tags"].items())))
    for name, s in o["schemas"].items():
        fq = "%s.%s" % (c["name"], name)
        spark.sql("CREATE SCHEMA IF NOT EXISTS %s" % fq)
        spark.sql("COMMENT ON SCHEMA %s IS '%s'" % (fq, esc(s["comment"])))
        spark.sql("ALTER SCHEMA %s SET TAGS ('owner' = '%s', 'layer' = '%s')" % (fq, s["owner"], s["layer"]))
    return len(o["schemas"])


def apply_grants(spark, dry_run=False):
    a = config.load_yaml("definitions/governance/access.yml")
    stmts = []
    for g in a["grants"]:
        for priv in g["privileges"]:
            stmts.append("GRANT %s ON %s %s TO `%s`" % (priv, g["on"]["type"], g["on"]["name"], g["principal"]))
    if not dry_run:
        for s in stmts:
            spark.sql(s)
    return stmts


def apply_masks(spark):
    m = config.load_yaml("definitions/governance/masking.yml")
    done = []
    for mk in m["masks"]:
        spark.sql("CREATE SCHEMA IF NOT EXISTS %s" % mk["schema"])
        allowed = " OR ".join("is_account_group_member('%s')" % g for g in mk["allowed_groups"])
        fn = "%s.%s" % (mk["schema"], mk["name"])
        spark.sql("CREATE OR REPLACE FUNCTION %s(%s) RETURNS %s COMMENT '%s' RETURN %s"
                  % (fn, mk["argument"], mk["returns"], esc(mk["description"]), mk["function_sql"].format(allowed=allowed)))
        spark.sql("ALTER TABLE %s ALTER COLUMN %s SET MASK %s" % (mk["table"], mk["column"], fn))
        done.append(fn)
    return done


def lineage_report(spark):
    """Walk Unity Catalog table lineage upstream from each Gold product and store the paths (system.access.table_lineage)."""
    cfg = config.load_yaml("definitions/governance/lineage.yml")
    rows = []
    for prod in cfg["products"]:
        frontier, seen = [prod], {prod}
        for depth in range(1, cfg["max_depth"] + 1):
            if not frontier:
                break
            up = (spark.table("system.access.table_lineage")
                  .where(F.col("target_table_full_name").isin(frontier) & F.col("source_table_full_name").isNotNull())
                  .select("source_table_full_name", "target_table_full_name").distinct().collect())
            frontier = []
            for r in up:
                rows.append((prod, depth, r["source_table_full_name"], r["target_table_full_name"]))
                if r["source_table_full_name"] not in seen:
                    seen.add(r["source_table_full_name"]); frontier.append(r["source_table_full_name"])
    df = spark.createDataFrame(rows, "data_product string, depth int, upstream_table string, downstream_table string") \
              .withColumn("reported_ts", F.current_timestamp())
    df.write.mode("overwrite").saveAsTable(cfg["report_table"])
    return len(rows)


def trace_record(spark, entity, key_value):
    """Follow one canonical record back to its Bronze row, landing file/batch, DQ results and run log (uses the lineage columns)."""
    t = config.load_yaml("definitions/governance/lineage.yml")["record_trace"][entity]
    s = spark.table(t["silver_table"]).where(F.col(t["key"]) == key_value)
    srow = s.collect()
    if not srow:
        return {"found": False}
    r = srow[0].asDict()
    b = spark.table(t["bronze_table"]).where(F.col("_row_hash") == r["_bronze_row_hash"])
    runs = spark.table("edap.audit.ingestion_runs").where(F.col("batch_id").isin(r["_landing_batch_id"], r["_bronze_batch_id"], r["_silver_batch_id"]))
    return {"found": True,
            "silver": {k: str(v) for k, v in r.items() if k.startswith("_") or k == t["key"]},
            "bronze_rows": [x.asDict() for x in b.select("_source_file", "_batch_id", "_landing_batch_id", "_ingest_ts", "_spec_path").collect()],
            "pipeline_runs": [x.asDict() for x in runs.select("layer", "table_name", "status", "rows_processed", "started_ts", "run_id").collect()]}
