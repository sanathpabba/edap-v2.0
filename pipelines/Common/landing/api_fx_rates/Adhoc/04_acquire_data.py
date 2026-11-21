"""Common / landing / api_fx_rates / Adhoc - step 04: Read from the source system (file list from the source drop for files).
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "api-loads/fx_rates"
STEP = {"order": 4, "name": "acquire_data", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.acquire_data(ctx)
