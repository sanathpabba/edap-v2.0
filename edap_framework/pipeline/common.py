"""Helpers shared by the step modules of every layer."""
import datetime as dt
import functools

from edap_framework.core import audit

LAYER_SCHEMAS = {"landing": [], "bronze": ["bronze"], "silver": ["silver", "reference"], "gold": ["gold"]}
BASE_SCHEMAS = ["audit", "metadata", "quarantine", "monitoring"]


def init_context(ctx):
    """Step 01 for every layer: make sure the schemas this layer needs exist, start the clock for this item."""
    ctx.st.clear()
    ctx.st["started"] = dt.datetime.utcnow()
    for s in BASE_SCHEMAS + LAYER_SCHEMAS[ctx.layer]:
        ctx.spark.sql("CREATE SCHEMA IF NOT EXISTS %s.%s" % (ctx.env["catalog"], s))


def skippable(fn):
    """A step is skipped when an earlier step marked the item as having nothing to do (e.g. no new rows)."""
    @functools.wraps(fn)
    def wrapper(ctx, *a, **k):
        if ctx.st.get("skip"):
            return None
        return fn(ctx, *a, **k)
    return wrapper


def log_run(ctx, status, rows, details):
    audit.log_run(ctx.spark, "%s.audit.ingestion_runs" % ctx.env["catalog"], batch_id=ctx.batch_id, run_id=ctx.run_id, layer=ctx.layer,
                  source_system=ctx.ac.name, table_name=ctx.item, scenario=ctx.scenario, status=status, rows_processed=rows,
                  started_ts=ctx.st.get("started"), finished_ts=dt.datetime.utcnow(), details=details)
