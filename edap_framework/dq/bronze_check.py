"""Run Bronze DQ for every Bronze batch that has not been checked yet (Bronze keeps all rows; DQ flags/quarantines copies)."""
from pyspark.sql import functions as F

from edap_framework.core import config
from edap_framework.dq.engine import apply_rule_set, load_rule_set


def check_bronze_table(spark, bronze_spec, env):
    rule_set = load_rule_set(bronze_spec["dq"]["rules_file"])
    fq = rule_set["target_table"]
    res = "%s.monitoring.dq_results" % env["catalog"]
    done = set()
    if spark.catalog.tableExists(res):
        done = {r[0] for r in spark.table(res).where(F.col("table_name") == fq).select("batch_id").distinct().collect()}
    batches = [r[0] for r in spark.table(fq).select("_batch_id").distinct().collect() if r[0] not in done]
    out = {}
    for b in sorted(batches):
        _, stats = apply_rule_set(spark, spark.table(fq).where(F.col("_batch_id") == b), rule_set, env, b, table_name=fq)
        out[b] = stats
    return out
