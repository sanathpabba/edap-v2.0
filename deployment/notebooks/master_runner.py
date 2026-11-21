# Databricks notebook source
# MAGIC %md
# MAGIC # EDAP master runner
# MAGIC Triggers the pipeline jobs **in order**: `edap-common` (landing, bronze, silver, gold) first, then every selected asset class **in parallel**
# MAGIC (`edap-equities`, `edap-fixedincome`, `edap-fx`, `edap-commodities`: bronze, silver, gold, consumption). If Common fails, the asset classes are not started.
# MAGIC
# MAGIC | Widget | Meaning |
# MAGIC |---|---|
# MAGIC | `asset_classes` | `ALL` or a comma list: `Common,Equities,FixedIncome,FX,Commodities` |
# MAGIC | `stages` | comma list of `landing,bronze,silver,gold,consumption` (empty = all) |
# MAGIC | `mode` | `Routine` = scheduled incremental run, `Adhoc` = initial load / backfill / replay / rebuild |
# MAGIC | `run_date` | `YYYY-MM-DD` (empty = today). The positions file expected and the FX day follow it |
# MAGIC | `expect_file` | `auto` = true for Routine, false for Adhoc. `true` halts the run if the expected file is missing |
# MAGIC | `from_ts`, `to_ts` | Adhoc replay window, ISO format without spaces: `2026-11-17T00:00:00` |
# MAGIC | `fx_mode` | FX pull: `daily` or `history` (empty = by mode) |
# MAGIC | `rescan`, `rebuild`, `notify` | re-check files already seen, recreate materialized views, send owner emails in Adhoc runs |
# MAGIC | `extra` | any more `key=value` pairs, space separated |
# MAGIC | `dry_run` | `true` = show the plan and check the jobs exist, trigger nothing |
# MAGIC | `wait` | `true` = wait for the runs and fail this notebook if any run fails |
# MAGIC
# MAGIC Run it from the notebook UI, or as a job with these as job parameters.

# COMMAND ----------

dbutils.widgets.text("wheel", "", "wheel (empty = newest in /Volumes/edap/metadata/artifacts)")

# COMMAND ----------

# Install the newest published framework wheel (by upload time), unless a wheel path is given.
import glob
import os
import subprocess
import sys

wheel = dbutils.widgets.get("wheel") or max(glob.glob("/Volumes/edap/metadata/artifacts/edap_framework-*.whl"), key=os.path.getmtime)
subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", wheel])
print("installed", wheel)

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("asset_classes", "ALL", "asset_classes")
dbutils.widgets.text("stages", "landing,bronze,silver,gold,consumption", "stages")
dbutils.widgets.dropdown("mode", "Routine", ["Routine", "Adhoc"], "mode")
dbutils.widgets.text("run_date", "", "run_date (YYYY-MM-DD, empty = today)")
dbutils.widgets.dropdown("expect_file", "auto", ["auto", "true", "false"], "expect_file")
dbutils.widgets.text("from_ts", "", "from_ts (Adhoc, e.g. 2026-11-17T00:00:00)")
dbutils.widgets.text("to_ts", "", "to_ts (Adhoc)")
dbutils.widgets.dropdown("fx_mode", "", ["", "daily", "history"], "fx_mode")
dbutils.widgets.dropdown("rescan", "false", ["false", "true"], "rescan")
dbutils.widgets.dropdown("rebuild", "false", ["false", "true"], "rebuild")
dbutils.widgets.dropdown("notify", "false", ["false", "true"], "notify")
dbutils.widgets.text("extra", "", "extra (key=value ...)")
dbutils.widgets.dropdown("dry_run", "false", ["false", "true"], "dry_run")
dbutils.widgets.dropdown("wait", "true", ["true", "false"], "wait")

# COMMAND ----------

import json

from databricks.sdk import WorkspaceClient

from edap_framework import master

get = dbutils.widgets.get
summary = master.run_master(
    WorkspaceClient(),
    asset_classes=get("asset_classes"),
    stages=get("stages"),
    mode=get("mode"),
    date=get("run_date"),
    expect_file=get("expect_file"),
    extra=master.extra_tokens(get("from_ts"), get("to_ts"), get("fx_mode"), get("rescan") == "true", get("rebuild") == "true", get("notify") == "true", get("extra")),
    dry_run=get("dry_run") == "true",
    wait=get("wait") == "true",
)
dbutils.notebook.exit(json.dumps(summary, default=str))
