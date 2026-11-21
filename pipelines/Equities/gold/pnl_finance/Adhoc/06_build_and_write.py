"""Equities / gold / pnl_finance / Adhoc - step 06: Execute the SQL and write the Gold table.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "pnl_finance"
STEP = {"order": 6, "name": "build_and_write", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.build_and_write(ctx)
