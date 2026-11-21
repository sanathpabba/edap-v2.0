"""Common / landing / sql_instruments / Adhoc - step 04: Read from the source system (file list from the source drop for files).
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "sql-loads/instruments"
STEP = {"order": 4, "name": "acquire_data", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.acquire_data(ctx)
