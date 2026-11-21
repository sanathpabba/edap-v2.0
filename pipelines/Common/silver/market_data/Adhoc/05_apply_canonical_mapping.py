"""Common / silver / market_data / Adhoc - step 05: Map source columns to canonical columns.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "market_data"
STEP = {"order": 5, "name": "apply_canonical_mapping", "layer": "silver", "mode": "Adhoc"}


def run(ctx):
    steps.apply_canonical_mapping(ctx)
