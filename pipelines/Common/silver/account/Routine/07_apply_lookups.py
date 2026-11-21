"""Common / silver / account / Routine - step 07: Reference-data columns and referential flags.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "account"
STEP = {"order": 7, "name": "apply_lookups", "layer": "silver", "mode": "Routine"}


def run(ctx):
    steps.apply_lookups(ctx)
