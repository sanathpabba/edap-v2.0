"""Equities / silver / trade_event / Routine - step 09: Add Silver audit and lineage columns.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "trade_event"
STEP = {"order": 9, "name": "add_meta_properties", "layer": "silver", "mode": "Routine"}


def run(ctx):
    steps.add_meta_properties(ctx)
