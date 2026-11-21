"""Common / bronze / sql_instruments / Routine - step 05: Apply the spec's shaping (JSON extract, payload parse, extra columns).
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/instruments"
STEP = {"order": 5, "name": "shape_columns", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.shape_columns(ctx)
