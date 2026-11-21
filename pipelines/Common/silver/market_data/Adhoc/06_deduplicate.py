"""Common / silver / market_data / Adhoc - step 06: Keep one row per business key.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "market_data"
STEP = {"order": 6, "name": "deduplicate", "layer": "silver", "mode": "Adhoc"}


def run(ctx):
    steps.deduplicate(ctx)
