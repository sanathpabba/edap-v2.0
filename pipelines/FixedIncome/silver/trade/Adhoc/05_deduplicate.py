"""FixedIncome / silver / trade / Adhoc - step 05: Keep one row per business key.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "trade"
STEP = {"order": 5, "name": "deduplicate", "layer": "silver", "mode": "Adhoc"}


def run(ctx):
    steps.deduplicate(ctx)
