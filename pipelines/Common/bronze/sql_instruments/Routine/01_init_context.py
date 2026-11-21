"""Common / bronze / sql_instruments / Routine - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/instruments"
STEP = {"order": 1, "name": "init_context", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.init_context(ctx)
