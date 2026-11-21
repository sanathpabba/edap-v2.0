"""Common / landing / sql_portfolios / Routine - step 05: Write the raw files to landing.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "sql-loads/portfolios"
STEP = {"order": 5, "name": "write_landing_files", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.write_landing_files(ctx)
