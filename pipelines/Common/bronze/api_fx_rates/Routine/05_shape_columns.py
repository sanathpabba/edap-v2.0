"""Common / bronze / api_fx_rates / Routine - step 05: Apply the spec's shaping (JSON extract, payload parse, extra columns).
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "api-loads/fx_rates"
STEP = {"order": 5, "name": "shape_columns", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.shape_columns(ctx)
