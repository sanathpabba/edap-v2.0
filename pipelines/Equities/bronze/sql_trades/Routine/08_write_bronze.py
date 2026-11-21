"""Equities / bronze / sql_trades / Routine - step 08: Write the Bronze Delta table.

Routine mode: Streaming append with checkpoint.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/trades"
STEP = {"order": 8, "name": "write_bronze", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.write_bronze(ctx)
