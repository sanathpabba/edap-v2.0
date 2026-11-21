"""FX / silver / trade_event / Adhoc - step 03: Ensure the reference tables used by the lookups exist.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "trade_event"
STEP = {"order": 3, "name": "load_reference_data", "layer": "silver", "mode": "Adhoc"}


def run(ctx):
    steps.load_reference_data(ctx)
