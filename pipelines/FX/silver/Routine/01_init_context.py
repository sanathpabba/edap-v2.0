"""FX / silver / Routine - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import silver_steps as steps

STEP = {"order": 1, "name": "init_context", "layer": "silver", "mode": "Routine"}


def run(ctx):
    steps.init_context(ctx)
