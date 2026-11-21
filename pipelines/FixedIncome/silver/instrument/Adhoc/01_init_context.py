"""FixedIncome / silver / instrument / Adhoc - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "instrument"
STEP = {"order": 1, "name": "init_context", "layer": "silver", "mode": "Adhoc"}


def run(ctx):
    steps.init_context(ctx)
