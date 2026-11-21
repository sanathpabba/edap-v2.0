"""FixedIncome / consumption / trade_daily_mv / Adhoc - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "trade_daily_mv"
STEP = {"order": 1, "name": "init_context", "layer": "consumption", "mode": "Adhoc"}


def run(ctx):
    steps.init_context(ctx)
