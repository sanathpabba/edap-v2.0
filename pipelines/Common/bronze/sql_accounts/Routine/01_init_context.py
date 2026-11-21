"""Common / bronze / sql_accounts / Routine - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/accounts"
STEP = {"order": 1, "name": "init_context", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.init_context(ctx)
