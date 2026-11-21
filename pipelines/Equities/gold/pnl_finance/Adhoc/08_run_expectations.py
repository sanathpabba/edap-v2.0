"""Equities / gold / pnl_finance / Adhoc - step 08: Run DQX sanity checks (flag mode).
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "pnl_finance"
STEP = {"order": 8, "name": "run_expectations", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.run_expectations(ctx)
