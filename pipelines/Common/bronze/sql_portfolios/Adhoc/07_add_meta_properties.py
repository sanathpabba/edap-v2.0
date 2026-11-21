"""Common / bronze / sql_portfolios / Adhoc - step 07: Add audit and lineage columns.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/portfolios"
STEP = {"order": 7, "name": "add_meta_properties", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.add_meta_properties(ctx)
