"""Common / bronze / sql_portfolios / Adhoc - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/portfolios"
STEP = {"order": 1, "name": "init_context", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.init_context(ctx)
