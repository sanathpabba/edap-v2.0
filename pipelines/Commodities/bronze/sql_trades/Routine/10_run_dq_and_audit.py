"""Commodities / bronze / sql_trades / Routine - step 10: Run DQX at Bronze, close superseded quarantine rows, write the run log.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/trades"
STEP = {"order": 10, "name": "run_dq_and_audit", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.run_dq_and_audit(ctx)
