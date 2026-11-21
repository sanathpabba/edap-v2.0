"""FixedIncome / gold / trade_analytics / Adhoc - step 08: Run DQX expectations (flag mode).
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "trade_analytics"
STEP = {"order": 8, "name": "run_expectations", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.run_expectations(ctx)
