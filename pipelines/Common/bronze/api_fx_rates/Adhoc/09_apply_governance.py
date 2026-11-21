"""Common / bronze / api_fx_rates / Adhoc - step 09: Apply Unity Catalog comment and tags.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "api-loads/fx_rates"
STEP = {"order": 9, "name": "apply_governance", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.apply_governance(ctx)
