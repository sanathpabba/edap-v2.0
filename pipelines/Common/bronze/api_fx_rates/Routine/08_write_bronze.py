"""Common / bronze / api_fx_rates / Routine - step 08: Write the Bronze Delta table.

Routine mode: Streaming append with checkpoint.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "api-loads/fx_rates"
STEP = {"order": 8, "name": "write_bronze", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.write_bronze(ctx)
