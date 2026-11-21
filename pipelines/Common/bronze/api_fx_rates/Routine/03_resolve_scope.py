"""Common / bronze / api_fx_rates / Routine - step 03: Resolve the asset-class routing rule and the replay window.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "api-loads/fx_rates"
STEP = {"order": 3, "name": "resolve_scope", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.resolve_scope(ctx)
