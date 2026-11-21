"""Common / landing / sql_accounts / Routine - step 06: Write the raw files to landing (files: copy good files unchanged from the source drop).
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "sql-loads/accounts"
STEP = {"order": 6, "name": "write_landing_files", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.write_landing_files(ctx)
