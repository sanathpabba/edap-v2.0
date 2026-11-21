"""FixedIncome / consumption / trade_metrics / Adhoc - step 03: Check the Gold product it reads exists.
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "trade_metrics"
STEP = {"order": 3, "name": "check_upstream", "layer": "consumption", "mode": "Adhoc"}


def run(ctx):
    steps.check_upstream(ctx)
