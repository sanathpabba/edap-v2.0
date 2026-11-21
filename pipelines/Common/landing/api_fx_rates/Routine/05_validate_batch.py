"""Common / landing / api_fx_rates / Routine - step 05: Whole-file checks (received? readable? right header? not empty?); a wrong file is rejected and the owner emailed.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "api-loads/fx_rates"
STEP = {"order": 5, "name": "validate_batch", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.validate_batch(ctx)
