"""Common / gold / fx_rate_daily / Routine - step 08: Run DQX sanity checks (flag mode).
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "fx_rate_daily"
STEP = {"order": 8, "name": "run_expectations", "layer": "gold", "mode": "Routine"}


def run(ctx):
    steps.run_expectations(ctx)
