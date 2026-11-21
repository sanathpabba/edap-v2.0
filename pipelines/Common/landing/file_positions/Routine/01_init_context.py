"""Common / landing / file_positions / Routine - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "file-loads/positions"
STEP = {"order": 1, "name": "init_context", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.init_context(ctx)
