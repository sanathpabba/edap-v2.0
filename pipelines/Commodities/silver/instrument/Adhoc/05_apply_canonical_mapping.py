"""Commodities / silver / instrument / Adhoc - step 05: Map source columns to canonical columns.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "instrument"
STEP = {"order": 5, "name": "apply_canonical_mapping", "layer": "silver", "mode": "Adhoc"}


def run(ctx):
    steps.apply_canonical_mapping(ctx)
