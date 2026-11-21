"""FX / gold / pnl_finance / Routine - step 08: Run DQX expectations (flag mode).
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "pnl_finance"
STEP = {"order": 8, "name": "run_expectations", "layer": "gold", "mode": "Routine"}


def run(ctx):
    steps.run_expectations(ctx)
