"""Landing steps 01-09 (one function per step file). The source type comes from the item folder: sql-loads, file-loads, stream-loads, api-loads.
File sources: source drop -> whole-file checks -> copy to landing -> registry. A wrong or missing file halts the pipeline (owner is emailed)."""
import datetime as dt

from edap_framework.core import config
from edap_framework.ingestion.files import arrival
from edap_framework.ingestion.rest_api import fx_pull
from edap_framework.ingestion.sql import extract
from edap_framework.ingestion.streaming import eventhub_to_landing as stream
from edap_framework.pipeline import common
from edap_framework.pipeline.common import PipelineHalt, skippable

init_context = common.init_context


def _kind(ctx):
    return ctx.item.split("/")[0]


def read_source_yaml(ctx):
    """02 - read the landing spec and the source contract it points to."""
    st = ctx.st
    st["spec_path"] = "definitions/landing/%s.yml" % ctx.item
    st["spec"] = config.load_yaml(st["spec_path"], ctx.variables)
    st["source"] = config.load_yaml(st["spec"]["source_definition"])


def resolve_extract_window(ctx):
    """03 - decide what to fetch: SQL watermark window, FX mode/date, file expectations, event offsets."""
    st, k, p = ctx.st, _kind(ctx), ctx.params
    if k == "sql-loads":
        st["lo"], st["hi"] = extract.resolve_window(ctx.spark, st["spec"], ctx.env, ctx.is_adhoc, p.get("from_ts"))
        st["skip"] = st["hi"] is None
        if st["skip"]:
            common.log_run(ctx, "NO_DATA", 0, "source table empty")
    elif k == "api-loads":
        st["fx_mode"] = p.get("fx_mode") or ("history" if ctx.is_adhoc else "daily")
        st["date"] = p.get("date") or dt.datetime.utcnow().date().isoformat()
    elif k == "file-loads":
        st["rescan"] = ctx.is_adhoc and bool(p.get("rescan"))
        st["expect_file"] = str(p.get("expect_file", "")).lower() in ("true", "1", "yes")
        st["today"] = dt.date.fromisoformat(p["date"]) if p.get("date") else dt.datetime.utcnow().date()
    elif k == "stream-loads":
        st["namespace"] = ctx.env.get("eventhub_namespace")


@skippable
def acquire_data(ctx):
    """04 - read from the source (JDBC DataFrame / API response / source-drop file list / Event Hubs stream)."""
    st, k = ctx.st, _kind(ctx)
    if k == "sql-loads":
        st["df"] = extract.read_extract(ctx.spark, st["spec"], ctx.env, st["lo"], st["hi"])
    elif k == "api-loads":
        try:
            st["result"] = fx_pull.fetch_fx(st["spec"], st["fx_mode"], st["date"])
        except RuntimeError as exc:                                              # the API never answered: data not received
            st["halt"] = str(exc)
            common.send_notification(ctx, "SOURCE_NOT_RECEIVED", "HALT", "Data not received from the source API", [str(exc)],
                                     counts={"requested date": st["date"], "mode": st["fx_mode"]})
            st["skip"] = True
            common.log_run(ctx, "HALTED", 0, st["halt"])
            raise PipelineHalt(st["halt"])
    elif k == "file-loads":
        st["all_files"] = arrival.scan_source_drop(ctx.spark, st["spec"], ctx.env, st["rescan"])
        st["files"] = [f for f in st["all_files"] if f["new"]]
        st["rows"], st["good"], st["bad"] = [], [], []
    elif k == "stream-loads":
        st["df"] = stream.build_event_stream(ctx.spark, st["spec"], ctx.env, st["namespace"], ctx.batch_id)


@skippable
def validate_batch(ctx):
    """05 - whole-file / whole-batch checks BEFORE anything lands. Files: expected file received? readable? right header? not empty?
    A wrong file is rejected to quarantine and the pipeline will halt; a stale API answer only warns."""
    st, k = ctx.st, _kind(ctx)
    if k == "file-loads":
        spec = st["spec"]
        if st["expect_file"]:
            missing = arrival.check_expected_file(spec, st["all_files"], st["today"])
            if missing:
                st["halt"] = missing
                common.send_notification(ctx, "FILE_NOT_RECEIVED", "HALT", "Expected file was not received", [missing],
                                         counts={"files found in source drop": len(st["all_files"])})
        for f in st["files"]:
            problems = arrival.check_file(ctx.spark, spec, ctx.env, f)
            if not problems:
                st["good"].append(f)
                continue
            qpath = arrival.quarantine_file(ctx.spark, spec, ctx.env, f)
            st["bad"].append(f)
            st["rows"].append(arrival.registry_row(f, qpath, ctx.batch_id, "REJECTED"))
            st["halt"] = "file %s rejected: %s" % (f["name"], "; ".join(problems))
            common.send_notification(ctx, "FILE_REJECTED", "HALT", "The whole file is wrong and was rejected: %s" % f["name"], problems,
                                     counts={"file": f["name"], "size (bytes)": f["size"], "business date": f["business_date"]},
                                     links=["Rejected copy: %s" % qpath, "File registry: SELECT * FROM %s WHERE status = 'REJECTED'" % spec["registry"]["table"]])
    elif k == "api-loads" and st["result"]["stale"]:
        common.send_notification(ctx, "API_STALE", "WARN", "API returned the previous business day (weekend/holiday)",
                                 ["requested %s but the API answered for an earlier date; file stored with a _stale suffix" % st["date"]])


@skippable
def write_landing_files(ctx):
    """06 - write the raw files to landing (files: copy the good ones, unchanged, from the source drop into landing/inbound)."""
    st, k = ctx.st, _kind(ctx)
    if k == "sql-loads":
        st["path"], st["count"] = extract.write_extract(ctx.spark, st["spec"], ctx.env, st["df"], ctx.batch_id)
    elif k == "api-loads":
        st["path"], st["count"] = fx_pull.write_fx(ctx.spark, st["spec"], ctx.env, st["result"]), 1
    elif k == "file-loads":
        for f in st["good"]:
            st["rows"].append(arrival.registry_row(f, arrival.copy_to_landing(ctx.spark, st["spec"], ctx.env, f), ctx.batch_id, "REGISTERED"))
        st["path"], st["count"] = None, len(st["good"])
    elif k == "stream-loads":
        st["path"], st["count"] = None, stream.write_event_stream(ctx.spark, st["spec"], ctx.env, st["df"], ctx.batch_id, ctx.is_adhoc)


@skippable
def register_landing_batch(ctx):
    """07 - register what landed or was rejected (file registry for files and FX; SQL and events are located by their batch_id folder)."""
    st, k = ctx.st, _kind(ctx)
    if k == "api-loads":
        fx_pull.register_fx(ctx.spark, st["spec"], st["result"], st["path"], ctx.batch_id)
    elif k == "file-loads":
        arrival.register_arrivals(ctx.spark, st["spec"], st["rows"])


@skippable
def advance_watermark(ctx):
    """08 - SQL only: move the watermark forward after the files are safely written."""
    if _kind(ctx) == "sql-loads" and ctx.st["spec"]["watermark"].get("advance_after_success", True):
        extract.commit_watermark(ctx.spark, ctx.st["spec"], ctx.st["hi"], ctx.batch_id)


def audit_log(ctx):
    """09 - run-log entry; if a whole file was missing/wrong, record HALTED and stop the pipeline (the owner was already emailed)."""
    st = ctx.st
    if st.get("skip") and not st.get("halt"):
        return
    if st.get("halt"):
        common.log_run(ctx, "HALTED", st.get("count", 0), st["halt"])
        raise PipelineHalt(st["halt"])
    status = "STALE" if st.get("result", {}).get("stale") else "SUCCESS"
    common.log_run(ctx, status, st.get("count", 0), st.get("path") or "%s landed" % ctx.item)
