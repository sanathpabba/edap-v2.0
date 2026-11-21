"""Gold steps 01-09 (one function per step file). Item = data product name (e.g. trade_analytics)."""
from edap_framework.core import config
from edap_framework.gold import builder
from edap_framework.pipeline import common

init_context = common.init_context


def read_product_yaml(ctx):
    """02 - read the data product definition (documentation, CTEs, joins, dimensions, measures, parameters)."""
    st = ctx.st
    st["spec_path"] = "definitions/gold_products/%s.yml" % ctx.item
    st["product"] = config.load_yaml(st["spec_path"], ctx.variables)
    t = st["product"]["target"]
    st["fq"] = "%s.%s.%s" % (t["catalog"], t["schema"], t["table"])


def resolve_parameters(ctx):
    """03 - product parameters from YAML, overridden by run parameters (Adhoc what-if runs: --param name=value)."""
    st = ctx.st
    st["params"] = builder.resolve_parameters(st["product"], ctx.params.get("product_params") if ctx.is_adhoc else None)


def check_upstream(ctx):
    """04 - fail early with a clear message when an upstream table is missing or empty."""
    builder.check_upstream(ctx.spark, ctx.st["product"])


def compose_sql(ctx):
    """05 - compose the product SQL from the YAML."""
    st = ctx.st
    st["sql"] = builder.compose_sql(st["product"], st["params"])


def build_and_write(ctx):
    """06 - execute the SQL and write the Gold table."""
    st = ctx.st
    st["count"] = builder.write_product(ctx.spark, st["sql"], st["product"])


def apply_documentation(ctx):
    """07 - business purpose, grain, owner, refresh and consumers as Unity Catalog comment and tags."""
    st = ctx.st
    builder.document(ctx.spark, st["product"], st["spec_path"], ctx.ac.name)


def run_expectations(ctx):
    """08 - DQX expectations on the product (flag mode: results recorded, rows kept)."""
    st = ctx.st
    st["dq"] = builder.run_expectations(ctx.spark, st["product"], ctx.env, ctx.batch_id, ctx.variables)


def audit_log(ctx):
    """09 - run log entry."""
    st = ctx.st
    common.log_run(ctx, "SUCCESS", st["count"], "-> %s; dq %s" % (st["fq"], st["dq"]))
