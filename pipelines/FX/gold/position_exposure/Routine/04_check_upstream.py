"""FX / gold / position_exposure / Routine - step 04: Check upstream tables exist and are not empty.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "position_exposure"
STEP = {"order": 4, "name": "check_upstream", "layer": "gold", "mode": "Routine"}


def run(ctx):
    steps.check_upstream(ctx)
