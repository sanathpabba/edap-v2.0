"""Common / gold / fx_rate_daily / Adhoc - step 08: Run DQX expectations (flag mode).
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "fx_rate_daily"
STEP = {"order": 8, "name": "run_expectations", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.run_expectations(ctx)
