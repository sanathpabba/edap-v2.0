"""Equities / gold / trade_analytics / Adhoc - step 07: Apply purpose, grain, owner, refresh as comment and tags.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "trade_analytics"
STEP = {"order": 7, "name": "apply_documentation", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.apply_documentation(ctx)
