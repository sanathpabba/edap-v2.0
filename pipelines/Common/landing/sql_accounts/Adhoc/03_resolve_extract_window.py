"""Common / landing / sql_accounts / Adhoc - step 03: Decide what to fetch (watermark window, FX date, file rescan, event offsets).

Adhoc mode: SQL: --from-ts or a full re-extract. FX: history. Files: --rescan re-registers. Events: replay from the earliest offset.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "sql-loads/accounts"
STEP = {"order": 3, "name": "resolve_extract_window", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.resolve_extract_window(ctx)
