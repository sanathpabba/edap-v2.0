"""FixedIncome / gold / regulatory_reporting / Routine - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "regulatory_reporting"
STEP = {"order": 1, "name": "init_context", "layer": "gold", "mode": "Routine"}


def run(ctx):
    steps.init_context(ctx)
