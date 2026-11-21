"""FX / gold / pnl_finance / Routine - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "pnl_finance"
STEP = {"order": 1, "name": "init_context", "layer": "gold", "mode": "Routine"}


def run(ctx):
    steps.init_context(ctx)
