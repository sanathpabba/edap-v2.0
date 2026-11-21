"""FX / bronze / file_positions / Adhoc - step 07: Add audit and lineage columns.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "file-loads/positions"
STEP = {"order": 7, "name": "add_meta_properties", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.add_meta_properties(ctx)
