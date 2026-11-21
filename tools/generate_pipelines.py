"""Generate the pipeline folder tree from the asset-class definitions and the step tables below.

  pipelines/<AssetClass>/<layer>/<table>/<Routine|Adhoc>/NN_<step>.py   (each file = one framework function call)
  deployment/jobs.yml                                           (Databricks jobs wired to the same folders)

Edit LAYER_STEPS to change the sequence, then re-run:  python tools/generate_pipelines.py
The files are intentionally thin: the logic lives in edap_framework/pipeline/<layer>_steps.py."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.environ["EDAP_PROJECT_ROOT"] = ROOT
from edap_framework.core import config  # noqa: E402

# (function name, title, routine note, adhoc note)
LAYER_STEPS = {
    "landing": [
        ("init_context", "Initialise the run: schemas, run id, clock", "", ""),
        ("read_source_yaml", "Read the landing spec and the source contract", "", ""),
        ("resolve_extract_window", "Decide what to fetch (watermark window, FX date, file rescan, event offsets)",
         "SQL: stored watermark .. current max. FX: today's daily rates. Files: only new files.",
         "SQL: --from-ts or a full re-extract. FX: history. Files: --rescan re-registers. Events: replay from the earliest offset."),
        ("acquire_data", "Read from the source system", "", ""),
        ("write_landing_files", "Write the raw files to landing", "", ""),
        ("register_landing_batch", "Register the landed batch (file registry)", "", ""),
        ("advance_watermark", "Advance the SQL watermark after a successful write", "", "Only moves forward; an Adhoc backfill never lowers it."),
        ("audit_log", "Write the run-log entry", "", ""),
    ],
    "bronze": [
        ("init_context", "Initialise the run: schemas, run id, clock", "", ""),
        ("read_source_yaml", "Read the Bronze spec, landing spec and source contract", "", ""),
        ("resolve_scope", "Resolve the asset-class routing rule and the replay window", "", "Replay window from --from-ts / --to-ts."),
        ("read_landing", "Read the landing files", "Auto Loader stream (availableNow): only new files.",
         "Batch read of landing files in the replay window."),
        ("shape_columns", "Apply the spec's shaping (JSON extract, payload parse, extra columns)", "", ""),
        ("route_to_asset_class", "Keep only this asset class's rows", "", ""),
        ("add_meta_properties", "Add audit and lineage columns", "", ""),
        ("write_bronze", "Write the Bronze Delta table", "Streaming append with checkpoint.", "Delete the replayed landing batches, then append: no duplicates."),
        ("apply_governance", "Apply Unity Catalog comment and tags", "", ""),
        ("run_dq_and_audit", "Run DQX at Bronze, close superseded quarantine rows, write the run log", "", ""),
    ],
    "silver": [
        ("init_context", "Initialise the run: schemas, run id, clock", "", ""),
        ("read_mapping_yaml", "Read the canonical mapping for the entity", "", ""),
        ("load_reference_data", "Ensure the reference tables used by the lookups exist", "", ""),
        ("read_bronze_increment", "Read new Bronze rows, minus DQ-quarantined rows", "Since the Silver watermark.", "Since --from-ts, or everything (full rebuild)."),
        ("apply_canonical_mapping", "Map source columns to canonical columns", "", ""),
        ("deduplicate", "Keep one row per business key", "", ""),
        ("apply_lookups", "Reference-data columns and referential flags", "", ""),
        ("run_dq_silver", "Run DQX business rules, quarantine invalid rows", "", ""),
        ("add_meta_properties", "Add Silver audit and lineage columns", "", ""),
        ("merge_and_finalize", "MERGE into the canonical table, advance the watermark, tag, log", "", "The watermark only moves forward."),
    ],
    "gold": [
        ("init_context", "Initialise the run: schemas, run id, clock", "", ""),
        ("read_product_yaml", "Read the data product definition", "", ""),
        ("resolve_parameters", "Resolve product parameters", "YAML defaults.", "YAML defaults overridden by --param name=value (what-if runs)."),
        ("check_upstream", "Check upstream tables exist and are not empty", "", ""),
        ("compose_sql", "Compose the product SQL from the YAML", "", ""),
        ("build_and_write", "Execute the SQL and write the Gold table", "", ""),
        ("apply_documentation", "Apply purpose, grain, owner, refresh as comment and tags", "", ""),
        ("run_expectations", "Run DQX expectations (flag mode)", "", ""),
        ("audit_log", "Write the run-log entry", "", ""),
    ],
}
MODES = ["Routine", "Adhoc"]
README = """# Pipelines

`pipelines/<AssetClass>/<layer>/<table>/<Routine|Adhoc>/NN_<step>.py`

- **One folder per table** (bronze/landing: `sql_trades`, `file_positions` ...; silver: entity; gold: data product), so an asset class can hold
  hundreds of tables and each keeps its own step files. The tables of a layer are listed, in run order, in `definitions/asset_classes/*.yml`.

- **Asset classes:** Equities, FixedIncome, FX, Commodities, plus **Common** (landing for every source, instrument master, portfolios, accounts,
  counterparties, FX rates, the conformed FX dimension). Common runs first.
- **Layers:** landing (Common only), bronze, silver, gold.
- **Routine** = the scheduled incremental run. **Adhoc** = on demand: initial load, backfill, replay, rebuild, what-if.
- **Each numbered file calls one framework function** (`edap_framework/pipeline/<layer>_steps.py`); the order of the files is the pipeline.
  The runner executes each table's steps in order, table after table.

```bash
python pipelines/run.py --asset-class Equities --layer bronze --mode Routine
python pipelines/run.py --asset-class Equities --layer silver --mode Adhoc --item trade --from-ts 2026-11-17     # one table
python pipelines/run.py --asset-class Equities --layer bronze --mode Routine --steps 1-5 --dry-run      # show the plan
python pipelines/run.py --asset-class ALL --layer silver --mode Routine                                  # Common, then every asset class
```
Regenerate this tree after editing the step tables: `python tools/generate_pipelines.py`.
"""


def step_file(ac, layer, item, mode, order, fn, title, rnote, anote):
    note = (anote if mode == "Adhoc" else rnote)
    note_txt = "\n%s mode: %s\n" % (mode, note) if note else ""
    return '''"""%s / %s / %s / %s - step %02d: %s.
%s"""
from edap_framework.pipeline import %s_steps as steps

ITEM = "%s"
STEP = {"order": %d, "name": "%s", "layer": "%s", "mode": "%s"}


def run(ctx):
    steps.%s(ctx)
''' % (ac.folder, layer, config.table_folder(layer, item), mode, order, title, note_txt, layer, item, order, fn, layer, mode, fn)


def generate():
    import shutil
    written = 0
    acs = config.list_asset_classes()
    for ac in acs:                                                   # rebuild the asset class tree from scratch (drops stale tables)
        shutil.rmtree(os.path.join(ROOT, "pipelines", ac.folder), ignore_errors=True)
    for ac in acs:
        for layer, steps in LAYER_STEPS.items():
            for item in ac.items.get(layer, []):
                for mode in MODES:
                    d = os.path.join(ROOT, "pipelines", ac.folder, layer, config.table_folder(layer, item), mode)
                    os.makedirs(d, exist_ok=True)
                    for i, (fn, title, rn, an) in enumerate(steps, 1):
                        open(os.path.join(d, "%02d_%s.py" % (i, fn)), "w").write(step_file(ac, layer, item, mode, i, fn, title, rn, an))
                        written += 1
    open(os.path.join(ROOT, "pipelines", "README.md"), "w").write(README)
    write_jobs(acs)
    return written


def _task(key, ac, layer, mode, deps, extra=()):
    t = {"task_key": key, "environment_key": "edap_env", "depends_on": [{"task_key": d} for d in deps],
         "spark_python_task": {"python_file": "../pipelines/run.py",
                               "parameters": ["--asset-class", ac, "--layer", layer, "--mode", mode, "--run-id", "{{job.run_id}}", *extra]}}
    if not deps:
        del t["depends_on"]
    return t


def write_jobs(acs):
    import yaml
    env = [{"environment_key": "edap_env", "spec": {"environment_version": "2", "dependencies": ["pyyaml", "requests", "databricks-labs-dqx"]}}]
    ac_names = [a.folder for a in acs if a.prefix != "common"]
    tasks = [_task("common_landing", "Common", "landing", "Routine", []), _task("common_bronze", "Common", "bronze", "Routine", ["common_landing"]),
             _task("common_silver", "Common", "silver", "Routine", ["common_bronze"]), _task("common_gold", "Common", "gold", "Routine", ["common_silver"])]
    for n in ac_names:
        k = n.lower()
        tasks += [_task(k + "_bronze", n, "bronze", "Routine", ["common_bronze"]),
                  _task(k + "_silver", n, "silver", "Routine", [k + "_bronze", "common_silver"]),
                  _task(k + "_gold", n, "gold", "Routine", [k + "_silver", "common_gold"])]
    jobs = {
        "edap_routine_daily": {"name": "edap-routine-daily", "schedule": {"quartz_cron_expression": "0 0 6 * * ?", "timezone_id": "UTC", "pause_status": "PAUSED"},
                               "environments": env, "tasks": tasks},
        "edap_positions_on_file_arrival": {
            "name": "edap-positions-on-file-arrival", "environments": env,
            "trigger": {"pause_status": "PAUSED", "file_arrival": {"url": "abfss://landing@edapdl.dfs.core.windows.net/positions/inbound/"}},
            "tasks": [_task("landing_positions", "Common", "landing", "Routine", [], ["--item", "file-loads/positions"])]
                     + [t for n in ac_names for t in (_task(n.lower() + "_bronze_positions", n, "bronze", "Routine", ["landing_positions"], ["--item", "file-loads/positions"]),
                                                      _task(n.lower() + "_silver_position", n, "silver", "Routine", [n.lower() + "_bronze_positions"], ["--item", "position"]))]},
        "edap_trade_events_drain": {
            "name": "edap-trade-events-drain", "environments": env,
            "schedule": {"quartz_cron_expression": "0 0/15 * * * ?", "timezone_id": "UTC", "pause_status": "PAUSED"},
            "tasks": [_task("landing_events", "Common", "landing", "Routine", [], ["--item", "stream-loads/trade_events"])]
                     + [t for n in ac_names for t in (_task(n.lower() + "_bronze_events", n, "bronze", "Routine", ["landing_events"], ["--item", "stream-loads/trade_events"]),
                                                     _task(n.lower() + "_silver_event", n, "silver", "Routine", [n.lower() + "_bronze_events"], ["--item", "trade_event"]))]},
        "edap_adhoc": {
            "name": "edap-adhoc (initial load / backfill / replay / rebuild)", "environments": env,
            "parameters": [{"name": "asset_class", "default": "Equities"}, {"name": "layer", "default": "bronze"}, {"name": "extra", "default": ""}],
            "tasks": [{"task_key": "adhoc", "environment_key": "edap_env", "spark_python_task": {
                "python_file": "../pipelines/run.py",
                "parameters": ["--asset-class", "{{job.parameters.asset_class}}", "--layer", "{{job.parameters.layer}}", "--mode", "Adhoc",
                               "--run-id", "{{job.run_id}}", "--extra", "{{job.parameters.extra}}"]}}]},
    }
    head = ("# Databricks jobs generated by tools/generate_pipelines.py from the pipeline folders. NOT yet deployed or validated.\n"
            "# Common runs first; each asset class then runs bronze -> silver -> gold. Re-generate instead of editing by hand.\n")
    open(os.path.join(ROOT, "deployment", "jobs.yml"), "w").write(head + yaml.dump({"resources": {"jobs": jobs}}, sort_keys=False, width=200))


if __name__ == "__main__":
    print(generate(), "step files written")
