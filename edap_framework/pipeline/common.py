"""Helpers shared by the step modules of every layer."""
import datetime as dt
import functools

from edap_framework.core import audit, config
from edap_framework.notify import notifier

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


class PipelineFailure(Exception):
    """One or more tables failed with an unexpected error. Raised after every other table of the layer has been processed."""


class PipelineHalt(Exception):
    """The whole file/batch is wrong or missing: stop the pipeline so downstream layers do not start. Raised after the owner was notified."""


def pipeline_info(ctx):
    return {"asset_class": ctx.ac.name, "layer": ctx.layer, "table": config.table_folder(ctx.layer, ctx.item), "mode": ctx.mode}


def owner_of(ctx):
    """Owner = the owner tag of the item's spec (landing: notify.owner, bronze/silver/gold: governance.owner)."""
    st = ctx.st
    for key in ("spec", "mapping", "product"):
        obj = st.get(key)
        if obj:
            return ((obj.get("notify") or {}).get("owner") or (obj.get("governance") or {}).get("owner")
                    or (obj.get("documentation") or {}).get("owner"))
    return None


def send_notification(ctx, kind, severity, headline, reasons=None, rules=None, samples=None, counts=None, links=None, notify_on=None):
    """Owner email for this item. Adhoc runs are quiet unless --extra notify=true. notify_on (halt|warn|pass) filters by severity."""
    if notify_on is not None and severity.lower() not in notify_on:
        return "SKIPPED_BY_NOTIFY_ON"
    quiet = ctx.is_adhoc and str(ctx.params.get("notify", "")).lower() not in ("true", "1", "yes")
    event = {"kind": kind, "severity": severity, "pipeline": pipeline_info(ctx), "run_id": ctx.run_id, "batch_id": ctx.batch_id, "owner": owner_of(ctx),
             "headline": headline, "reasons": reasons or [], "rules": rules or [], "samples": samples or [], "counts": counts or {}, "links": links or []}
    status = notifier.notify(ctx.spark, ctx.env, event, send=not quiet)
    ctx.st.setdefault("notifications", []).append((kind, severity, status))
    return status


def gate_and_notify(ctx, stats_list, spec_gate, fq, layer):
    """Evaluate the DQ gate for the stats of the batches just checked, email the owner (halt/warn), and return the worst decision.
    Returns None when nothing was checked. Halting is the caller's job (it logs the run first, then raises PipelineHalt)."""
    from edap_framework.dq import gate
    if not stats_list:
        return None
    settings = gate.gate_settings(spec_gate)
    decisions = [gate.evaluate(s, settings) for s in stats_list]
    status = "HALT" if any(d.halt for d in decisions) else ("WARN" if any(d.status == "WARN" for d in decisions) else "PASS")
    total, failed = sum(s["total"] for s in stats_list), sum(s["failed_rows"] for s in stats_list)
    merged = {}
    for s in stats_list:
        for r in s.get("rules", []):
            m = merged.setdefault(r["rule"], {"rule": r["rule"], "criticality": r["criticality"], "failed_rows": 0, "total_rows": 0})
            m["failed_rows"] += r["failed_rows"]; m["total_rows"] += r["total_rows"]
    rules = sorted(merged.values(), key=lambda r: -r["failed_rows"])
    samples = [x for s in stats_list for x in s.get("samples", [])][:5]
    reasons = [r for d in decisions for r in d.reasons]
    headline = {"HALT": "Data quality failed - the whole batch is wrong, downstream not started",
                "WARN": "%d of %d rows failed data quality and were quarantined; pipeline continued" % (failed, total),
                "PASS": "Data quality passed"}[status]
    inv = "%s.quarantine.%s_invalid" % (ctx.env["catalog"], layer)
    links = ["Quarantined rows: SELECT * FROM %s WHERE table_name = '%s' AND status = 'OPEN'" % (inv, fq),
             "Rule results:    SELECT * FROM %s.monitoring.dq_results WHERE table_name = '%s' ORDER BY checked_ts DESC" % (ctx.env["catalog"], fq)]
    counts = {"rows checked": total, "rows failed (error rules)": failed, "failure rate": "%.1f%%" % (100.0 * failed / total if total else 0),
              "rows with warnings": sum(s.get("warned", 0) for s in stats_list), "halt limit": "%.0f%%" % (settings["max_error_rate"] * 100)}
    if status != "PASS":
        send_notification(ctx, "DQ_" + status, status, headline, reasons, rules, samples, counts, links, notify_on=settings["notify_on"])
    ctx.st["gate"] = {"status": status, "reasons": reasons}
    return status
