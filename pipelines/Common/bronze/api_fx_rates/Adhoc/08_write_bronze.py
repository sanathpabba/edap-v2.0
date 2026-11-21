"""Common / bronze / api_fx_rates / Adhoc - step 08: Write the Bronze Delta table and apply Unity Catalog comment and tags.

Adhoc mode: Delete the replayed landing batches, then append: no duplicates.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "api-loads/fx_rates"
STEP = {"order": 8, "name": "write_bronze", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.write_bronze(ctx)
