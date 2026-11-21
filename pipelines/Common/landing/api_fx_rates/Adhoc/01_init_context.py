"""Common / landing / api_fx_rates / Adhoc - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "api-loads/fx_rates"
STEP = {"order": 1, "name": "init_context", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.init_context(ctx)
