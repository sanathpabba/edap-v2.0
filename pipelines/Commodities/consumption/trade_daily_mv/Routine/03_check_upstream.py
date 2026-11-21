"""Commodities / consumption / trade_daily_mv / Routine - step 03: Check the Gold product it reads exists.
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "trade_daily_mv"
STEP = {"order": 3, "name": "check_upstream", "layer": "consumption", "mode": "Routine"}


def run(ctx):
    steps.check_upstream(ctx)
