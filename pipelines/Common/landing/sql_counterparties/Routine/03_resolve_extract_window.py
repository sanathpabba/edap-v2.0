"""Common / landing / sql_counterparties / Routine - step 03: Decide what to fetch (watermark window, FX date, file rescan, event offsets).

Routine mode: SQL: stored watermark .. current max. FX: today's daily rates. Files: only new files.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "sql-loads/counterparties"
STEP = {"order": 3, "name": "resolve_extract_window", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.resolve_extract_window(ctx)
