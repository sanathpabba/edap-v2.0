"""Common / landing / sql_instruments / Adhoc - step 06: Write the raw files to landing (files: copy good files unchanged from the source drop).
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "sql-loads/instruments"
STEP = {"order": 6, "name": "write_landing_files", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.write_landing_files(ctx)
