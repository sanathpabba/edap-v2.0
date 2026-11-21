"""Common / landing / api_fx_rates / Adhoc - step 06: Register the landed batch (file registry).
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "api-loads/fx_rates"
STEP = {"order": 6, "name": "register_landing_batch", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.register_landing_batch(ctx)
