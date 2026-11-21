"""Equities / bronze / file_positions / Adhoc - step 05: Apply the spec's shaping (JSON extract, payload parse, extra columns).
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "file-loads/positions"
STEP = {"order": 5, "name": "shape_columns", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.shape_columns(ctx)
