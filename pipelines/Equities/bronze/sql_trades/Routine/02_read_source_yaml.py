"""Equities / bronze / sql_trades / Routine - step 02: Read the Bronze spec, landing spec and source contract.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/trades"
STEP = {"order": 2, "name": "read_source_yaml", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.read_source_yaml(ctx)
