"""Common / silver / counterparty / Adhoc - step 07: Reference-data columns and referential flags.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "counterparty"
STEP = {"order": 7, "name": "apply_lookups", "layer": "silver", "mode": "Adhoc"}


def run(ctx):
    steps.apply_lookups(ctx)
