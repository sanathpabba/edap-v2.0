"""Common / bronze / api_fx_rates / Routine - step 07: Add audit and lineage columns.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "api-loads/fx_rates"
STEP = {"order": 7, "name": "add_meta_properties", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.add_meta_properties(ctx)
