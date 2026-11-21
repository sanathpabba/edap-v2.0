"""Common / landing / api_fx_rates / Adhoc - step 05: Write the raw files to landing.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "api-loads/fx_rates"
STEP = {"order": 5, "name": "write_landing_files", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.write_landing_files(ctx)
