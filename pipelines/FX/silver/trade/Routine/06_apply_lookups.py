"""FX / silver / trade / Routine - step 06: Reference-data columns and referential flags (loads missing reference tables).
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "trade"
STEP = {"order": 6, "name": "apply_lookups", "layer": "silver", "mode": "Routine"}


def run(ctx):
    steps.apply_lookups(ctx)
