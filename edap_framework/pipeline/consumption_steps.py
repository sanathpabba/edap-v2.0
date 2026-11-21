"""Consumption steps 01-08 (one function per step file). Item = metric view / materialized view name (e.g. trade_metrics)."""
from edap_framework.consumption import builder
from edap_framework.core import config
from edap_framework.pipeline import common

init_context = common.init_context


def read_consumption_yaml(ctx):
    """02 - read the consumption definition (kind, source Gold product, metric view YAML or materialized view SELECT)."""
    st = ctx.st
    st["spec_path"] = "definitions/consumption/%s.yml" % ctx.item
    st["spec"] = config.load_yaml(st["spec_path"], ctx.variables)
    st["fq"] = builder.fq_name(st["spec"])


def check_upstream(ctx):
    """03 - the Gold product this object reads must exist (fail early with a clear message)."""
    src = ctx.st["spec"]["source"]
    if not ctx.spark.catalog.tableExists(src):
        raise RuntimeError("Consumption %s blocked: Gold table %s does not exist yet (run the gold stage first)" % (ctx.st["fq"], src))


def compose_sql(ctx):
    """04 - compose the statement: CREATE ... WITH METRICS, or CREATE / REFRESH MATERIALIZED VIEW (Adhoc rebuild=true recreates it)."""
    st = ctx.st
    exists = ctx.spark.catalog.tableExists(st["fq"])
    rebuild = str(ctx.params.get("rebuild", "")).lower() in ("true", "1", "yes")
    st["statement"] = builder.compose_statement(st["spec"], exists=exists, rebuild=rebuild)
    st["action"] = st["statement"].split("\n")[0][:60]


def create_or_refresh(ctx):
    """05 - run the statement (job compute, or the configured SQL warehouse)."""
    builder.run_sql(ctx.spark, ctx.env, ctx.st["statement"])


def apply_documentation(ctx):
    """06 - purpose, grain, owner, refresh and consumers as tags (best effort; failures are recorded, not fatal)."""
    st = ctx.st
    st["doc_warnings"] = builder.document(ctx.spark, ctx.env, st["spec"], st["spec_path"], ctx.ac.name)


def verify_object(ctx):
    """07 - prove the object works: a MEASURE() query for metric views, a row count for materialized views."""
    st = ctx.st
    rows = builder.run_sql(ctx.spark, ctx.env, builder.verify_statement(st["spec"]))
    st["verified"] = rows[0][0] if rows else None
    st["count"] = int(rows[0][0]) if rows and st["spec"]["kind"] == "materialized_view" and rows[0][0] is not None else 0


def audit_log(ctx):
    """08 - run-log entry."""
    st = ctx.st
    common.log_run(ctx, "SUCCESS", st.get("count", 0), "%s -> %s; verified=%s%s" % (st["action"], st["fq"], st.get("verified"),
                                                                                 ("; doc: " + "; ".join(st["doc_warnings"])) if st.get("doc_warnings") else ""))
