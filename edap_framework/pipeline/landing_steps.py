"""Landing steps 01-08 (one function per step file). The source type comes from the item folder: sql-loads, file-loads, stream-loads, api-loads."""
import datetime as dt

from edap_framework.core import config
from edap_framework.ingestion.files import arrival
from edap_framework.ingestion.rest_api import fx_pull
from edap_framework.ingestion.sql import extract
from edap_framework.ingestion.streaming import eventhub_to_landing as stream
from edap_framework.pipeline import common
from edap_framework.pipeline.common import skippable

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
    """03 - decide what to fetch: SQL watermark window, FX mode/date, file rescan flag, event offsets."""
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
    elif k == "stream-loads":
        st["namespace"] = ctx.env.get("eventhub_namespace")


@skippable
def acquire_data(ctx):
    """04 - read from the source (JDBC DataFrame / API response / file list / Event Hubs stream)."""
    st, k = ctx.st, _kind(ctx)
    if k == "sql-loads":
        st["df"] = extract.read_extract(ctx.spark, st["spec"], ctx.env, st["lo"], st["hi"])
    elif k == "api-loads":
        st["result"] = fx_pull.fetch_fx(st["spec"], st["fx_mode"], st["date"])
    elif k == "file-loads":
        st["rows"] = arrival.scan_arrivals(ctx.spark, st["spec"], ctx.env, ctx.batch_id, st["rescan"])
    elif k == "stream-loads":
        st["df"] = stream.build_event_stream(ctx.spark, st["spec"], ctx.env, st["namespace"], ctx.batch_id)


@skippable
def write_landing_files(ctx):
    """05 - write the raw files to landing (files: the inbound folder already is the landing zone)."""
    st, k = ctx.st, _kind(ctx)
    if k == "sql-loads":
        st["path"], st["count"] = extract.write_extract(ctx.spark, st["spec"], ctx.env, st["df"], ctx.batch_id)
    elif k == "api-loads":
        st["path"], st["count"] = fx_pull.write_fx(ctx.spark, st["spec"], ctx.env, st["result"]), 1
    elif k == "file-loads":
        st["path"], st["count"] = None, len(st["rows"])
    elif k == "stream-loads":
        st["path"], st["count"] = None, stream.write_event_stream(ctx.spark, st["spec"], ctx.env, st["df"], ctx.batch_id, ctx.is_adhoc)


@skippable
def register_landing_batch(ctx):
    """06 - register what landed (file registry for files and FX; SQL and events are located by their batch_id folder)."""
    st, k = ctx.st, _kind(ctx)
    if k == "api-loads":
        fx_pull.register_fx(ctx.spark, st["spec"], st["result"], st["path"], ctx.batch_id)
    elif k == "file-loads":
        arrival.register_arrivals(ctx.spark, st["spec"], st["rows"])


@skippable
def advance_watermark(ctx):
    """07 - SQL only: move the watermark forward after the files are safely written."""
    if _kind(ctx) == "sql-loads" and st_advance(ctx):
        extract.commit_watermark(ctx.spark, ctx.st["spec"], ctx.st["hi"], ctx.batch_id)


def st_advance(ctx):
    return ctx.st["spec"]["watermark"].get("advance_after_success", True)


def audit_log(ctx):
    """08 - run log entry for this item."""
    st = ctx.st
    if st.get("skip"):
        return
    status = "STALE" if st.get("result", {}).get("stale") else "SUCCESS"
    common.log_run(ctx, status, st.get("count", 0), st.get("path") or "%s landed" % ctx.item)
