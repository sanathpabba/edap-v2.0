"""Common / landing / api_fx_rates / Routine - step 07: Register the landed/rejected files (file registry).
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "api-loads/fx_rates"
STEP = {"order": 7, "name": "register_landing_batch", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.register_landing_batch(ctx)
