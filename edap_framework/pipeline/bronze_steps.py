"""Bronze steps 01-10 (one function per step file)."""
from edap_framework.bronze import loader
from edap_framework.core import config
from edap_framework.dq.bronze_check import check_bronze_table
from edap_framework.dq.quarantine import close_superseded_by_resend
from edap_framework.pipeline import common

init_context = common.init_context


def read_source_yaml(ctx):
    """02 - read the Bronze spec, the landing spec it consumes and the source contract."""
    st = ctx.st
    st["spec_path"] = "definitions/bronze/%s.yml" % ctx.item
    st["spec"] = config.load_yaml(st["spec_path"], ctx.variables)
    st["landing_spec"] = config.load_yaml(st["spec"]["input"]["landing_spec"])
    st["source"] = config.load_yaml(st["landing_spec"]["source_definition"])
    st["fq"] = "%s.%s.%s" % (st["spec"]["target"]["catalog"], st["spec"]["target"]["schema"], st["spec"]["target"]["table"])


def resolve_scope(ctx):
    """03 - what this run covers: the asset-class routing rule and (Adhoc) the replay window."""
    st = ctx.st
    st["scope"] = st["spec"].get("scope") or {"by": "none"}
    st["window"] = (ctx.params.get("from_ts"), ctx.params.get("to_ts")) if ctx.is_adhoc else (None, None)
    if st["scope"]["by"] == "instrument" and not ctx.spark.catalog.tableExists(loader.INSTRUMENT_MASTER):
        raise RuntimeError("Run Common/bronze first: %s is needed to route rows to asset classes" % loader.INSTRUMENT_MASTER)


def read_landing(ctx):
    """04 - read the landing files (Auto Loader stream for Routine, batch window for Adhoc)."""
    st = ctx.st
    st["df"] = loader.read_landing(ctx.spark, st["spec"], ctx.env, ctx.is_adhoc, *st["window"])


def shape_columns(ctx):
    """05 - apply the spec's shaping (JSON extract, payload parse, extra columns)."""
    ctx.st["df"] = loader.shape_columns(ctx.st["df"], ctx.st["spec"])


def route_to_asset_class(ctx):
    """06 - keep only this asset class's rows (no-op for shared sources)."""
    ctx.st["df"] = loader.route_to_asset_class(ctx.spark, ctx.st["df"], ctx.st["spec"], ctx.ac)


def add_meta_properties(ctx):
    """07 - add audit and lineage columns (landing batch, row hash, run id, spec path/version, ingest time)."""
    st = ctx.st
    st["df"] = loader.add_meta_properties(ctx.spark, st["df"], st["spec"], ctx.batch_id, st["spec_path"], ctx.run_id)


def write_bronze(ctx):
    """08 - append to the Bronze Delta table (Adhoc: replay without duplicating)."""
    st = ctx.st
    st["count"] = loader.write_bronze(ctx.spark, st["df"], st["spec"], ctx.env, ctx.batch_id, ctx.is_adhoc)


def apply_governance(ctx):
    """09 - Unity Catalog comment and tags from the spec's governance block."""
    loader.apply_governance(ctx.spark, ctx.st["spec"], ctx.st["spec_path"], ctx.ac.name)


def run_dq_and_audit(ctx):
    """10 - DQX at Bronze (quarantine bad rows), close superseded quarantine rows for corrected resends, write the run log."""
    st = ctx.st
    st["dq"] = check_bronze_table(ctx.spark, st["spec"], ctx.env, ctx.variables, ctx.params.get("recheck_batches"))
    if ctx.item.startswith("file-loads/"):
        close_superseded_by_resend(ctx.spark, ctx.env, st["fq"])
    common.log_run(ctx, "SUCCESS", st["count"], "-> %s; dq %s" % (st["fq"], st["dq"]))
