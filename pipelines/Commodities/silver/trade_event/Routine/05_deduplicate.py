"""Commodities / silver / trade_event / Routine - step 05: Keep one row per business key.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "trade_event"
STEP = {"order": 5, "name": "deduplicate", "layer": "silver", "mode": "Routine"}


def run(ctx):
    steps.deduplicate(ctx)
