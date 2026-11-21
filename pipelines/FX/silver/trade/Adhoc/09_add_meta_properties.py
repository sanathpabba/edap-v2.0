"""FX / silver / trade / Adhoc - step 09: Add Silver audit and lineage columns.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "trade"
STEP = {"order": 9, "name": "add_meta_properties", "layer": "silver", "mode": "Adhoc"}


def run(ctx):
    steps.add_meta_properties(ctx)
