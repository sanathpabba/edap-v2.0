"""Common / bronze / sql_accounts / Adhoc - step 09: Run DQX at Bronze, quarantine failing rows, close rows superseded by a corrected file.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/accounts"
STEP = {"order": 9, "name": "run_dq", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.run_dq(ctx)
