"""Silver steps 01-10 (one function per step file). Item = entity name (e.g. trade)."""
from edap_framework.core import config
from edap_framework.pipeline import common
from edap_framework.pipeline.common import PipelineHalt, skippable
from edap_framework.silver import engine
from edap_framework.silver.reference import load_reference

init_context = common.init_context


def read_mapping_yaml(ctx):
    """02 - read the canonical mapping for this entity."""
    st = ctx.st
    st["spec_path"] = "definitions/mappings/%s.yml" % ctx.item
    st["mapping"] = config.load_yaml(st["spec_path"], ctx.variables)
    t = st["mapping"]["target"]
    st["fq"] = "%s.%s.%s" % (t["catalog"], t["schema"], t["table"])


def read_bronze_increment(ctx):
    """03 - new Bronze rows (Routine: since the Silver watermark; Adhoc: since from_ts or all), minus quarantined rows."""
    st = ctx.st
    st["df"], st["hi"] = engine.read_bronze_increment(ctx.spark, st["mapping"], ctx.env, ctx.ac.prefix, ctx.is_adhoc, ctx.params.get("from_ts"))
    st["skip"] = st["hi"] is None
    if st["skip"]:
        common.log_run(ctx, "NO_NEW_DATA", 0, "no new Bronze rows")


@skippable
def apply_canonical_mapping(ctx):
    """04 - source columns -> canonical columns (rename, cast, derive) as written in the mapping YAML."""
    ctx.st["df"] = engine.apply_canonical_mapping(ctx.st["df"], ctx.st["mapping"])


@skippable
def deduplicate(ctx):
    """05 - one row per business key (latest wins by the mapping's ordering)."""
    ctx.st["df"] = engine.deduplicate(ctx.st["df"], ctx.st["mapping"])


@skippable
def apply_lookups(ctx):
    """06 - reference-data columns and referential-integrity flags (loads a missing reference table first)."""
    st = ctx.st
    for lk in st["mapping"].get("lookups", []):
        if lk["table"].startswith("%s.reference." % ctx.env["catalog"]) and not ctx.spark.catalog.tableExists(lk["table"]):
            load_reference(ctx.spark, lk["table"].split(".")[-1], ctx.env)
    st["df"] = engine.apply_lookups(ctx.spark, st["df"], st["mapping"])


@skippable
def run_dq_silver(ctx):
    """07 - DQX business rules; invalid rows go to quarantine.silver_invalid."""
    st = ctx.st
    st["df"], st["dq"] = engine.run_dq(ctx.spark, st["df"], st["mapping"], ctx.env, ctx.batch_id, st["fq"], ctx.variables)


@skippable
def dq_gate_and_notify(ctx):
    """08 - DQ gate before anything is merged: only a whole-batch failure halts (Gold is not started, nothing merged, watermark not advanced).
    Otherwise the clean rows continue; the owner is emailed on a halt or warning with the failed checks."""
    st = ctx.st
    status = common.gate_and_notify(ctx, [st["dq"]], st["mapping"].get("gate"), st["fq"], "silver")
    if status == "HALT":
        common.log_run(ctx, "HALTED", 0, "; ".join(st["gate"]["reasons"]))
        raise PipelineHalt("Silver %s: %s" % (st["fq"], "; ".join(st["gate"]["reasons"])))


@skippable
def add_meta_properties(ctx):
    """09 - Silver audit and lineage columns."""
    st = ctx.st
    st["df"] = engine.add_silver_meta(st["df"], st["mapping"], ctx.batch_id, ctx.run_id, st["spec_path"])


@skippable
def merge_and_finalize(ctx):
    """10 - MERGE into the canonical table, advance the watermark, tag the table, write the run log."""
    st = ctx.st
    engine.merge_to_silver(ctx.spark, st["df"], st["mapping"], st["fq"])
    engine.advance_watermark(ctx.spark, ctx.env, st["mapping"], ctx.ac.prefix, st["hi"], ctx.batch_id, ctx.is_adhoc)
    engine.apply_governance(ctx.spark, st["fq"], st["mapping"], st["spec_path"], ctx.ac.name)
    n = st["dq"]["total"] - st["dq"]["quarantined"]
    common.log_run(ctx, "SUCCESS", n, "-> %s; dq %s" % (st["fq"], st["gate"]["status"] if st.get("gate") else "PASS"))
