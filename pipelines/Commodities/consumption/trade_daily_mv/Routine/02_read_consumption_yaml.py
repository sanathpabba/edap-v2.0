"""Commodities / consumption / trade_daily_mv / Routine - step 02: Read the metric view / materialized view definition.
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "trade_daily_mv"
STEP = {"order": 2, "name": "read_consumption_yaml", "layer": "consumption", "mode": "Routine"}


def run(ctx):
    steps.read_consumption_yaml(ctx)
