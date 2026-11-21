"""Common / landing / sql_portfolios / Routine - step 07: Register the landed/rejected files (file registry).
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "sql-loads/portfolios"
STEP = {"order": 7, "name": "register_landing_batch", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.register_landing_batch(ctx)
