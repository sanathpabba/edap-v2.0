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
        ("resolve_extract_window", "Decide what to fetch (watermark window, FX date, expected file, event offsets)",
         "SQL: stored watermark .. current max. FX: today's daily rates. Files: new files in the source drop.",
         "SQL: --from-ts or a full re-extract. FX: history. Files: --rescan re-checks files already seen. Events: replay from the earliest offset."),
        ("acquire_data", "Read from the source system (file list from the source drop for files)", "", ""),
        ("validate_batch", "Whole-file checks (received? readable? right header? not empty?); a wrong file is rejected and the owner emailed", "", ""),
        ("write_landing_files", "Write the raw files to landing (files: copy good files unchanged from the source drop)", "", ""),
        ("register_landing_batch", "Register the landed/rejected files (file registry)", "", ""),
        ("advance_watermark", "Advance the SQL watermark after a successful write", "", "Only moves forward; an Adhoc backfill never lowers it."),
        ("audit_log", "Write the run-log entry; halt the pipeline if a whole file was missing or wrong", "", ""),
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
        ("write_bronze", "Write the Bronze Delta table and apply Unity Catalog comment and tags", "Streaming append with checkpoint.", "Delete the replayed landing batches, then append: no duplicates."),
        ("run_dq", "Run DQX at Bronze, quarantine failing rows, close rows superseded by a corrected file", "", ""),
        ("dq_gate_and_notify", "DQ gate: halt only if the whole batch is wrong; email the owner on halt or warning; write the run log", "", ""),
    ],
    "silver": [
        ("init_context", "Initialise the run: schemas, run id, clock", "", ""),
        ("read_mapping_yaml", "Read the canonical mapping for the entity", "", ""),
        ("read_bronze_increment", "Read new Bronze rows, minus DQ-quarantined rows", "Since the Silver watermark.", "Since --from-ts, or everything (full rebuild)."),
        ("apply_canonical_mapping", "Map source columns to canonical columns", "", ""),
        ("deduplicate", "Keep one row per business key", "", ""),
        ("apply_lookups", "Reference-data columns and referential flags (loads missing reference tables)", "", ""),
        ("run_dq_silver", "Run DQX business rules, quarantine invalid rows", "", ""),
        ("dq_gate_and_notify", "DQ gate before the merge: halt only if the whole batch is wrong; email the owner on halt or warning", "", ""),
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
        ("run_expectations", "Run DQX sanity checks (flag mode)", "", ""),
        ("notify_and_audit_log", "Email the owner the failed sanity checks (if any); write the run-log entry", "", ""),
    ],
}
LAYER_STEPS["consumption"] = [
    ("init_context", "Initialise the run: schemas, run id, clock", "", ""),
    ("read_consumption_yaml", "Read the metric view / materialized view definition", "", ""),
    ("check_upstream", "Check the Gold product it reads exists", "", ""),
    ("compose_sql", "Compose CREATE ... WITH METRICS, or CREATE / REFRESH MATERIALIZED VIEW", "Materialized views are refreshed when they exist.",
     "--extra rebuild=true recreates a materialized view (use after changing its SELECT)."),
    ("create_or_refresh", "Run the statement (job compute or the configured SQL warehouse)", "", ""),
    ("apply_documentation", "Apply purpose, grain, owner, refresh as tags (best effort)", "", ""),
    ("verify_object", "Prove it works: a MEASURE() query or a row count", "", ""),
    ("audit_log", "Write the run-log entry", "", ""),
]
MODES = ["Routine", "Adhoc"]
README = """# Pipelines

`pipelines/<AssetClass>/<layer>/<table>/<Routine|Adhoc>/NN_<step>.py`

- **One folder per table** (bronze/landing: `sql_trades`, `file_positions` ...; silver: entity; gold: data product), so an asset class can hold
  hundreds of tables and each keeps its own step files. The tables of a layer are listed, in run order, in `definitions/asset_classes/*.yml`.

- **Asset classes:** Equities, FixedIncome, FX, Commodities, plus **Common** (landing for every source, instrument master, portfolios, accounts,
  counterparties, FX rates, the conformed FX dimension). Common runs first.
- **Layers:** landing (Common only), bronze, silver, gold, consumption (asset classes only: metric views and materialized views over Gold).
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
         "python_wheel_task": {"package_name": "edap_framework", "entry_point": "edap-run",
                               "parameters": ["--asset-class", ac, "--layer", layer, "--mode", mode, "--run-id", "{{job.run_id}}", *extra]}}
    if not deps:
        del t["depends_on"]
    return t


STAGES = ["landing", "bronze", "silver", "gold", "consumption"]
# job parameters shared by every pipeline job and the master job (the master_runner notebook passes the same names)
JOB_PARAMS = [{"name": "mode", "default": "Routine"}, {"name": "stages", "default": ",".join(STAGES)}, {"name": "date", "default": ""},
              {"name": "expect_file", "default": "true"}, {"name": "extra", "default": ""}]


def job_key(ac):
    return "edap_" + ac.folder.lower()


def job_name(ac):
    return "edap-" + ac.folder.lower()


def _stage_task(ac, layer, previous):
    """One stage of a pipeline job: edap-run for this asset class and layer. The job parameters choose mode and stages (a stage not in `stages` exits cleanly)."""
    extra = "date={{job.parameters.date}} {{job.parameters.extra}}"
    if layer == "landing":
        extra = "expect_file={{job.parameters.expect_file}} " + extra            # expected-file halt (daily run); the master turns it off for Adhoc
    t = {"task_key": "%s_%s" % (ac.folder.lower(), layer), "environment_key": "edap_env", "depends_on": [{"task_key": previous}] if previous else [],
         "python_wheel_task": {"package_name": "edap_framework", "entry_point": "edap-run",
                               "parameters": ["--asset-class", ac.folder, "--layer", layer, "--mode", "{{job.parameters.mode}}", "--stages", "{{job.parameters.stages}}",
                                              "--run-id", "{{job.run_id}}", "--extra", extra]}}
    if not previous:
        del t["depends_on"]
    return t


def write_jobs(acs):
    import yaml
    # The wheel (tools/build_wheel.py, published to the UC volume by CI or tools/publish_wheel.sh) carries the code, definitions and pipelines.
    # Jobs install it from the volume path in the bundle variable wheel_path; environment version 4 (Python 3.12) is the one verified on serverless.
    env = [{"environment_key": "edap_env", "spec": {"environment_version": "4", "dependencies": ["${var.wheel_path}", "databricks-labs-dqx==0.17.2"]}}]
    ac_names = [a.folder for a in acs if a.prefix != "common"]
    jobs = {}
    # one job per pipeline: its stages in order (Common: landing, bronze, silver, gold; asset classes: bronze, silver, gold, consumption)
    for ac in sorted(acs, key=lambda a: (a.prefix != "common", a.folder)):
        stage_tasks, prev = [], None
        for layer in STAGES:
            if layer in ac.items:
                stage_tasks.append(_stage_task(ac, layer, prev))
                prev = stage_tasks[-1]["task_key"]
        jobs[job_key(ac)] = {"name": job_name(ac), "parameters": JOB_PARAMS, "environments": env, "tasks": stage_tasks}
    # the master job: Common first, then every asset class in parallel; all parameters pass straight through to the pipeline jobs
    passthrough = {p["name"]: "{{job.parameters.%s}}" % p["name"] for p in JOB_PARAMS}
    master_tasks = [{"task_key": "common", "run_job_task": {"job_id": "${resources.jobs.edap_common.id}", "job_parameters": passthrough}}]
    for ac in sorted((a for a in acs if a.prefix != "common"), key=lambda a: a.folder):
        master_tasks.append({"task_key": ac.folder.lower(), "depends_on": [{"task_key": "common"}],
                             "run_job_task": {"job_id": "${resources.jobs.%s.id}" % job_key(ac), "job_parameters": passthrough}})
    jobs["edap_master"] = {"name": "edap-master", "schedule": {"quartz_cron_expression": "0 0 6 * * ?", "timezone_id": "UTC", "pause_status": "PAUSED"},
                           "parameters": JOB_PARAMS, "tasks": master_tasks}
    jobs["edap_positions_on_file_arrival"] = {
        "name": "edap-positions-on-file-arrival", "environments": env,
        "trigger": {"pause_status": "PAUSED", "file_arrival": {"url": "abfss://landing@edapdl.dfs.core.windows.net/positions/inbound/"}},
        "tasks": [_task("landing_positions", "Common", "landing", "Routine", [], ["--item", "file-loads/positions"])]
                 + [t for n in ac_names for t in (_task(n.lower() + "_bronze_positions", n, "bronze", "Routine", ["landing_positions"], ["--item", "file-loads/positions"]),
                                                  _task(n.lower() + "_silver_position", n, "silver", "Routine", [n.lower() + "_bronze_positions"], ["--item", "position"]))]}
    jobs["edap_trade_events_drain"] = {
        "name": "edap-trade-events-drain", "environments": env,
        "schedule": {"quartz_cron_expression": "0 0/15 * * * ?", "timezone_id": "UTC", "pause_status": "PAUSED"},
        "tasks": [_task("landing_events", "Common", "landing", "Routine", [], ["--item", "stream-loads/trade_events"])]
                 + [t for n in ac_names for t in (_task(n.lower() + "_bronze_events", n, "bronze", "Routine", ["landing_events"], ["--item", "stream-loads/trade_events"]),
                                                  _task(n.lower() + "_silver_event", n, "silver", "Routine", [n.lower() + "_bronze_events"], ["--item", "trade_event"]))]}
    jobs["edap_adhoc"] = {
        "name": "edap-adhoc (one pipeline, one layer; initial load / backfill / replay / rebuild)", "environments": env,
        "parameters": [{"name": "asset_class", "default": "Equities"}, {"name": "layer", "default": "bronze"}, {"name": "extra", "default": ""}],
        "tasks": [{"task_key": "adhoc", "environment_key": "edap_env", "python_wheel_task": {
            "package_name": "edap_framework", "entry_point": "edap-run",
            "parameters": ["--asset-class", "{{job.parameters.asset_class}}", "--layer", "{{job.parameters.layer}}", "--mode", "Adhoc",
                           "--run-id", "{{job.run_id}}", "--extra", "{{job.parameters.extra}}"]}}]}
    fail_to = config.load_yaml("definitions/governance/notifications.yml").get("job_failure_recipients") or []
    if fail_to:                                              # crash safety net on top of the custom owner notifier
        for j in jobs.values():
            j["email_notifications"] = {"on_failure": fail_to}
    head = ("# Databricks jobs generated by tools/generate_pipelines.py from the pipeline folders. NOT yet deployed or validated.\n"
            "# Tasks run the installed wheel: python_wheel_task -> console command edap-run (see docs/runbooks/build_and_deploy.md).\n"
            "# One job per pipeline (edap-common, edap-equities, ...) with its stages as tasks, and edap-master which runs Common first, then the asset classes in parallel.\n"
            "# The master_runner notebook triggers these jobs with parameters (mode, stages, date, extra). Re-generate instead of editing by hand.\n")
    class NoAliasDumper(yaml.SafeDumper):                    # repeat shared blocks instead of writing &anchors/*aliases
        def ignore_aliases(self, data):
            return True
    open(os.path.join(ROOT, "deployment", "jobs.yml"), "w").write(head + yaml.dump({"resources": {"jobs": jobs}}, Dumper=NoAliasDumper, sort_keys=False, width=200))


if __name__ == "__main__":
    print(generate(), "step files written")
