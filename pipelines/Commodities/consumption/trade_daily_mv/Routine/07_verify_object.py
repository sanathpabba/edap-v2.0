"""Commodities / consumption / trade_daily_mv / Routine - step 07: Prove it works: a MEASURE() query or a row count.
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "trade_daily_mv"
STEP = {"order": 7, "name": "verify_object", "layer": "consumption", "mode": "Routine"}


def run(ctx):
    steps.verify_object(ctx)
