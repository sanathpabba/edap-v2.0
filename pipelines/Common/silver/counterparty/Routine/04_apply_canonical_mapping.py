"""Common / silver / counterparty / Routine - step 04: Map source columns to canonical columns.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "counterparty"
STEP = {"order": 4, "name": "apply_canonical_mapping", "layer": "silver", "mode": "Routine"}


def run(ctx):
    steps.apply_canonical_mapping(ctx)
