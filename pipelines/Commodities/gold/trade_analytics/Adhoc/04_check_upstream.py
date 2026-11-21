"""Commodities / gold / trade_analytics / Adhoc - step 04: Check upstream tables exist and are not empty.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "trade_analytics"
STEP = {"order": 4, "name": "check_upstream", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.check_upstream(ctx)
