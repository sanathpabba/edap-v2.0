"""Common / bronze / sql_portfolios / Adhoc - step 05: Apply the spec's shaping (JSON extract, payload parse, extra columns).
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/portfolios"
STEP = {"order": 5, "name": "shape_columns", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.shape_columns(ctx)
