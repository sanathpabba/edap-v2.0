"""Common / landing / Routine - step 06: Register the landed batch (file registry).
"""
from edap_framework.pipeline import landing_steps as steps

STEP = {"order": 6, "name": "register_landing_batch", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.register_landing_batch(ctx)
