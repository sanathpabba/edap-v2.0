"""Consumption building blocks (each is called by one pipeline step; see pipelines/*/consumption/*/NN_*.py).
Two kinds of object over the Gold products, both defined in YAML (definitions/consumption/*.yml):
  metric_view        CREATE OR REPLACE VIEW ... WITH METRICS LANGUAGE YAML   governed measures, re-aggregate for any dimension combination
  materialized_view  CREATE OR REPLACE MATERIALIZED VIEW ... AS SELECT       pre-computed table kept fresh with REFRESH
Statements run on the job's own compute (spark.sql) or, when environments/*.yml sets consumption.sql_warehouse_id, on that SQL warehouse."""
import time

import yaml

from edap_framework.core import spark_utils

KINDS = ("metric_view", "materialized_view")
esc = lambda s: str(s).replace("'", "''")


def fq_name(spec):
    return spark_utils.fq_table(spec["target"])


def metric_view_yaml(spec):
    """The YAML body of the metric view: version + source from the spec, then comment/dimensions/measures as written."""
    body = {"source": spec["source"], **spec["metric_view"]}
    text = "version: 1.1\n" + yaml.safe_dump(body, sort_keys=False, default_flow_style=False, width=200, allow_unicode=True)
    if "$$" in text:
        raise ValueError("metric view YAML must not contain '$$'")
    return text


def first_measure(spec):
    return spec["metric_view"]["measures"][0]["name"]


def compose_statement(spec, exists=False, rebuild=False):
    """The statement that creates or refreshes the object. Materialized views are refreshed when they exist (unless rebuild=True)."""
    fq, kind = fq_name(spec), spec["kind"]
    if kind == "metric_view":
        return "CREATE OR REPLACE VIEW %s\nWITH METRICS\nLANGUAGE YAML\nAS $$\n%s$$" % (fq, metric_view_yaml(spec))
    if kind == "materialized_view":
        if exists and not rebuild:
            return "REFRESH MATERIALIZED VIEW %s" % fq
        comment = spec["documentation"]["business_purpose"]
        return "CREATE OR REPLACE MATERIALIZED VIEW %s\nCOMMENT '%s'\nAS\n%s" % (fq, esc(comment), spec["materialized_view"]["select"].strip())
    raise ValueError("unknown consumption kind %r (expected one of %s)" % (kind, KINDS))


def verify_statement(spec):
    """A read that proves the object works: a measure query for metric views, a row count for materialized views."""
    fq = fq_name(spec)
    if spec["kind"] == "metric_view":
        return "SELECT MEASURE(`%s`) FROM %s" % (first_measure(spec), fq)
    return "SELECT COUNT(*) FROM %s" % fq


def _warehouse(env):
    return (env.get("consumption") or {}).get("sql_warehouse_id") or ""


def run_sql(spark, env, statement, poll_seconds=3, timeout_seconds=900):
    """Execute a statement; returns the rows (list of tuples)."""
    wid = _warehouse(env)
    if not wid:
        return [tuple(r) for r in spark.sql(statement).collect()]
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    r = w.statement_execution.execute_statement(warehouse_id=wid, statement=statement, wait_timeout="30s")
    deadline = time.time() + timeout_seconds
    while r.status.state.value in ("PENDING", "RUNNING") and time.time() < deadline:
        time.sleep(poll_seconds)
        r = w.statement_execution.get_statement(r.statement_id)
    if r.status.state.value != "SUCCEEDED":
        raise RuntimeError("SQL warehouse statement %s: %s" % (r.status.state.value, getattr(r.status.error, "message", "")))
    return [tuple(row) for row in ((r.result.data_array if r.result else None) or [])]


def document(spark, env, spec, spec_path, asset_class):
    """Comment and tags (best effort: the exact DDL differs between metric views and materialized views). Returns a list of warnings."""
    fq, d, warns = fq_name(spec), spec["documentation"], []
    tags = {"layer": "consumption", "asset_class": asset_class, "kind": spec["kind"], "owner": d["owner"], "sensitivity": d.get("sensitivity", "synthetic"),
            "grain": d["grain"], "refresh": d["refresh_pattern"], "spec": spec_path}
    for tag_stmt in ("ALTER VIEW %s SET TAGS (%s)", "ALTER TABLE %s SET TAGS (%s)"):
        try:
            run_sql(spark, env, tag_stmt % (fq, ", ".join("'%s' = '%s'" % (k, esc(v)) for k, v in tags.items())))
            break
        except Exception as exc:                                                    # noqa: BLE001
            warns.append("tags via '%s' failed: %s" % (tag_stmt.split(" %s")[0], str(exc)[:120]))
    else:
        return warns
    return []
