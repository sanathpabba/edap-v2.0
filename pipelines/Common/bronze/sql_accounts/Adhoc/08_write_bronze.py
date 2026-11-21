"""Common / bronze / sql_accounts / Adhoc - step 08: Write the Bronze Delta table.

Adhoc mode: Delete the replayed landing batches, then append: no duplicates.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/accounts"
STEP = {"order": 8, "name": "write_bronze", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.write_bronze(ctx)
