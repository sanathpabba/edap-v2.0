"""FixedIncome / silver / trade_event / Adhoc - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "trade_event"
STEP = {"order": 1, "name": "init_context", "layer": "silver", "mode": "Adhoc"}


def run(ctx):
    steps.init_context(ctx)
