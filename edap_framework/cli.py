"""Run a pipeline: an asset class (or ALL), one layer, one mode. Executes the ordinal step files in order for each table.
Installed as the console command `edap-run` (also: python -m edap_framework.cli, or pipelines/run.py in the repository).

  edap-run --asset-class Equities --layer bronze --mode Routine
  edap-run --asset-class Equities --layer silver --mode Adhoc --item trade --from-ts 2026-11-17
  edap-run --asset-class Equities --layer bronze --mode Routine --steps 1-5 --dry-run
  edap-run --asset-class ALL --layer silver --mode Routine        # Common first, then every asset class
Adhoc/extra parameters: --from-ts --to-ts --date --fx-mode --rescan --param name=value, or --extra "date=2026-11-17 fx_mode=daily"."""
import argparse
import sys

from edap_framework import __version__
from edap_framework.core import config
from edap_framework.pipeline.common import PipelineHalt
from edap_framework.pipeline.context import PipelineContext
from edap_framework.pipeline.sequence import run_sequence

LAYERS = ["landing", "bronze", "silver", "gold", "consumption"]


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version="edap-framework %s" % __version__)
    ap.add_argument("--asset-class", required=True, help="Equities | FixedIncome | FX | Commodities | Common | ALL")
    ap.add_argument("--layer", required=True, choices=LAYERS)
    ap.add_argument("--mode", default="Routine", choices=["Routine", "Adhoc"])
    ap.add_argument("--item", action="append", help="limit to these items (repeatable), e.g. file-loads/positions or trade")
    ap.add_argument("--steps", help="step range, e.g. 4-7 or 5")
    ap.add_argument("--stages", default="", help="comma list of layers to run (jobs pass the selected stages); a task whose --layer is not in it does nothing")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, run nothing (no Spark needed)")
    ap.add_argument("--run-id", default=None, help="Databricks job run id (jobs pass {{job.run_id}})")
    ap.add_argument("--scenario", default=None, help="label for the run log (d0/d1/d2)")
    ap.add_argument("--from-ts"); ap.add_argument("--to-ts"); ap.add_argument("--date"); ap.add_argument("--fx-mode", choices=["history", "daily"])
    ap.add_argument("--rescan", action="store_true"); ap.add_argument("--param", action="append", default=[], help="Gold what-if override name=value")
    ap.add_argument("--extra", default="", help='space-separated key=value pairs (for jobs): "date=2026-11-17 from_ts=2026-11-17"')
    return ap.parse_args(argv)


def build_params(a):
    p = {k: v for k, v in {"from_ts": a.from_ts, "to_ts": a.to_ts, "date": a.date, "fx_mode": a.fx_mode}.items() if v}
    if a.rescan:
        p["rescan"] = True
    pp = dict(x.split("=", 1) for x in a.param)
    for kv in a.extra.split():
        k, v = kv.split("=", 1)
        (pp if k.startswith("param.") else p)[k.replace("param.", "")] = v
    if pp:
        p["product_params"] = pp
    return p


def pipelines_for(name, layer):
    allac = config.list_asset_classes()
    chosen = allac if name.upper() == "ALL" else [config.get_asset_class(name)]
    chosen = sorted(chosen, key=lambda a: (a.prefix != "common", a.folder))          # Common first
    return [a for a in chosen if layer in a.items]


def stage_selected(layer, stages):
    """Empty/None = every stage. Otherwise the layer must be in the comma list."""
    chosen = [x.strip() for x in (stages or "").split(",") if x.strip()]
    return not chosen or layer in chosen


def main(argv=None):
    a = parse_args(argv)
    if not stage_selected(a.layer, a.stages):
        print("stage '%s' not selected (stages=%s): nothing to do" % (a.layer, a.stages))
        return 0
    first, last = 1, 99
    if a.steps:
        first, _, last = a.steps.partition("-")
        first, last = int(first), int(last or first)
    spark = env = None
    if not a.dry_run:
        from pyspark.sql import SparkSession
        spark, env = SparkSession.builder.getOrCreate(), config.load_env()
    total = 0
    for ac in pipelines_for(a.asset_class, a.layer):
        ctx = PipelineContext(ac, a.layer, a.mode, spark=spark, env=env, scenario=a.scenario, params=build_params(a), run_id=a.run_id)
        total += run_sequence(ctx, set(a.item) if a.item else None, first, last, a.dry_run)
    print("%d step executions%s" % (total, " (dry run)" if a.dry_run else ""))


if __name__ == "__main__":
    try:
        main()
    except PipelineHalt as halt:          # a whole file/batch was missing or wrong: the owner was notified; fail the task so downstream does not start
        print("PIPELINE HALTED: %s" % halt, file=sys.stderr)
        sys.exit(2)
