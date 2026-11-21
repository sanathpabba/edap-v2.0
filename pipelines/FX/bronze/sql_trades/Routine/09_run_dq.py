"""FX / bronze / sql_trades / Routine - step 09: Run DQX at Bronze, quarantine failing rows, close rows superseded by a corrected file.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/trades"
STEP = {"order": 9, "name": "run_dq", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.run_dq(ctx)
