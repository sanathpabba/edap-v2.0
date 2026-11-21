"""Common / bronze / sql_accounts / Routine - step 07: Add audit and lineage columns.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/accounts"
STEP = {"order": 7, "name": "add_meta_properties", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.add_meta_properties(ctx)
