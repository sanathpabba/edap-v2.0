"""DQ framework on top of Databricks Labs DQX (not custom SQL, not DLT expectations).
One rule file (definitions/dq_rules/<layer>/<name>.yml) = one rule set, applied to one DataFrame:
  - `checks` are plain DQX metadata checks (function / arguments / criticality), so anyone can add a rule by editing YAML
  - criticality error -> row is quarantined (mode: quarantine) ; warn -> row passes but the warning is recorded
  - outputs: valid rows, quarantine.<layer>_invalid (with reasons), monitoring.dq_results (per rule), monitoring.dq_summary (per run)
"""
import datetime as dt

from pyspark.sql import functions as F

from edap_framework.core import audit, config

QUARANTINE_DDL = """CREATE TABLE IF NOT EXISTS {t} (
  quarantine_id STRING, layer STRING, table_name STRING, rule_set STRING, batch_id STRING, run_id STRING,
  row_hash STRING, record_json STRING, failed_rules ARRAY<STRING>, errors_json STRING, warnings_json STRING,
  status STRING, quarantined_ts TIMESTAMP, resolved_ts TIMESTAMP, resolution STRING)"""
RESULTS_DDL = """CREATE TABLE IF NOT EXISTS {t} (
  dq_run_id STRING, run_id STRING, layer STRING, table_name STRING, rule_set STRING, batch_id STRING,
  rule_name STRING, criticality STRING, failed_rows BIGINT, total_rows BIGINT, checked_ts TIMESTAMP)"""
SUMMARY_DDL = """CREATE TABLE IF NOT EXISTS {t} (
  dq_run_id STRING, run_id STRING, layer STRING, table_name STRING, rule_set STRING, batch_id STRING,
  total_rows BIGINT, passed_rows BIGINT, quarantined_rows BIGINT, warned_rows BIGINT, pass_rate DOUBLE, checked_ts TIMESTAMP)"""


def load_rule_set(rel_path, variables=None):
    rs = config.load_yaml(rel_path, variables)
    rs["_path"] = rel_path
    return rs


def _dqx():
    from databricks.sdk import WorkspaceClient
    from databricks.labs.dqx.engine import DQEngine
    return DQEngine(WorkspaceClient())


def _tables(env):
    c = env["catalog"]
    return {"quarantine": lambda layer: "%s.quarantine.%s_invalid" % (c, layer),
            "results": "%s.monitoring.dq_results" % c, "summary": "%s.monitoring.dq_summary" % c}


def apply_rule_set(spark, df, rule_set, env, batch_id, table_name=None):
    """Apply a rule set to df. Returns (valid_df, stats). Quarantines error rows when mode=quarantine."""
    t = _tables(env)
    layer, mode = rule_set["layer"], rule_set.get("mode", "quarantine")
    table_name = table_name or rule_set["target_table"]
    dq_run = audit.new_batch_id()
    checked = _dqx().apply_checks_by_metadata(df, rule_set["checks"])          # adds _errors / _warnings
    has_err, has_warn = F.size("_errors") > 0, F.size("_warnings") > 0
    total = df.count()
    invalid = checked.where(has_err)
    n_bad = invalid.count()
    n_warn = checked.where(has_warn & ~has_err).count()
    valid = checked.where(~has_err).drop("_errors", "_warnings") if mode == "quarantine" else checked.drop("_errors", "_warnings")
    now = dt.datetime.utcnow()

    # per-rule results (errors and warnings)
    for col, crit in (("_errors", "error"), ("_warnings", "warn")):
        per_rule = checked.select(F.explode(col).alias("e")).groupBy("e.name").count().collect()
        names = {c["name"] for c in rule_set["checks"] if c.get("name")}
        rows = [(dq_run, audit.run_id(), layer, table_name, rule_set["rule_set"], batch_id, r["name"], crit, r["count"], total, now) for r in per_rule]
        seen = {r["name"] for r in per_rule}
        # rules that found nothing are recorded too (a passing rule is evidence as well)
        rows += [(dq_run, audit.run_id(), layer, table_name, rule_set["rule_set"], batch_id, n, c2.get("criticality", "error"), 0, total, now)
                 for c2 in rule_set["checks"] for n in [c2.get("name")] if n and n not in seen and c2.get("criticality", "error") == crit]
        if rows:
            spark.sql(RESULTS_DDL.format(t=t["results"]))
            spark.createDataFrame(rows, "dq_run_id string, run_id string, layer string, table_name string, rule_set string, batch_id string, "
                                        "rule_name string, criticality string, failed_rows long, total_rows long, checked_ts timestamp") \
                 .write.mode("append").saveAsTable(t["results"])

    # quarantine
    if mode == "quarantine" and n_bad:
        q = t["quarantine"](layer)
        spark.sql(QUARANTINE_DDL.format(t=q))
        payload = invalid.drop("_errors", "_warnings")
        hash_col = F.col("_row_hash") if "_row_hash" in payload.columns else F.sha2(F.to_json(F.struct(*payload.columns)), 256)
        (invalid.select(
            F.expr("uuid()").alias("quarantine_id"), F.lit(layer).alias("layer"), F.lit(table_name).alias("table_name"),
            F.lit(rule_set["rule_set"]).alias("rule_set"), F.lit(batch_id).alias("batch_id"), F.lit(audit.run_id()).alias("run_id"),
            hash_col.alias("row_hash"), F.to_json(F.struct(*payload.columns)).alias("record_json"),
            F.transform("_errors", lambda e: e["name"]).alias("failed_rules"),
            F.to_json("_errors").alias("errors_json"), F.to_json("_warnings").alias("warnings_json"),
            F.lit("OPEN").alias("status"), F.current_timestamp().alias("quarantined_ts"),
            F.lit(None).cast("timestamp").alias("resolved_ts"), F.lit(None).cast("string").alias("resolution"))
         .write.mode("append").saveAsTable(q))

    stats = {"total": total, "quarantined": n_bad if mode == "quarantine" else 0, "flagged": n_bad if mode == "flag" else 0, "warned": n_warn}
    passed = total - stats["quarantined"]
    spark.sql(SUMMARY_DDL.format(t=t["summary"]))
    spark.createDataFrame([(dq_run, audit.run_id(), layer, table_name, rule_set["rule_set"], batch_id, total, passed, stats["quarantined"] + stats["flagged"],
                            n_warn, (passed / total) if total else 1.0, now)],
                          "dq_run_id string, run_id string, layer string, table_name string, rule_set string, batch_id string, total_rows long, "
                          "passed_rows long, quarantined_rows long, warned_rows long, pass_rate double, checked_ts timestamp") \
         .write.mode("append").saveAsTable(t["summary"])
    return valid, stats
