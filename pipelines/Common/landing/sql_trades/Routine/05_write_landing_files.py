"""Common / landing / sql_trades / Routine - step 05: Write the raw files to landing.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "sql-loads/trades"
STEP = {"order": 5, "name": "write_landing_files", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.write_landing_files(ctx)
