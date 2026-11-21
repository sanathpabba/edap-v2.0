"""Commodities / silver / trade / Routine - step 05: Map source columns to canonical columns.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "trade"
STEP = {"order": 5, "name": "apply_canonical_mapping", "layer": "silver", "mode": "Routine"}


def run(ctx):
    steps.apply_canonical_mapping(ctx)
