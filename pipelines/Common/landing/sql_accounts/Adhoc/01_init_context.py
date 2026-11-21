"""Common / landing / sql_accounts / Adhoc - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "sql-loads/accounts"
STEP = {"order": 1, "name": "init_context", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.init_context(ctx)
