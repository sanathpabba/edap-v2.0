"""FixedIncome / gold / position_exposure / Adhoc - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "position_exposure"
STEP = {"order": 1, "name": "init_context", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.init_context(ctx)
