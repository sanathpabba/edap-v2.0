"""Common / gold / Adhoc - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import gold_steps as steps

STEP = {"order": 1, "name": "init_context", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.init_context(ctx)
