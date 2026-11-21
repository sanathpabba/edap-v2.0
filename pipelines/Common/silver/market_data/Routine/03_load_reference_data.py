"""Common / silver / market_data / Routine - step 03: Ensure the reference tables used by the lookups exist.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "market_data"
STEP = {"order": 3, "name": "load_reference_data", "layer": "silver", "mode": "Routine"}


def run(ctx):
    steps.load_reference_data(ctx)
