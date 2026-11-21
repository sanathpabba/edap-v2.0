"""Equities / silver / position / Routine - step 06: Keep one row per business key.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "position"
STEP = {"order": 6, "name": "deduplicate", "layer": "silver", "mode": "Routine"}


def run(ctx):
    steps.deduplicate(ctx)
