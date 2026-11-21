"""Commodities / gold / pnl_finance / Routine - step 07: Apply purpose, grain, owner, refresh as comment and tags.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "pnl_finance"
STEP = {"order": 7, "name": "apply_documentation", "layer": "gold", "mode": "Routine"}


def run(ctx):
    steps.apply_documentation(ctx)
