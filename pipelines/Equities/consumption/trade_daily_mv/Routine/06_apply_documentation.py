"""Equities / consumption / trade_daily_mv / Routine - step 06: Apply purpose, grain, owner, refresh as tags (best effort).
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "trade_daily_mv"
STEP = {"order": 6, "name": "apply_documentation", "layer": "consumption", "mode": "Routine"}


def run(ctx):
    steps.apply_documentation(ctx)
