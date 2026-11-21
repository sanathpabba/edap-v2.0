"""Commodities / bronze / file_positions / Routine - step 08: Write the Bronze Delta table and apply Unity Catalog comment and tags.

Routine mode: Streaming append with checkpoint.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "file-loads/positions"
STEP = {"order": 8, "name": "write_bronze", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.write_bronze(ctx)
