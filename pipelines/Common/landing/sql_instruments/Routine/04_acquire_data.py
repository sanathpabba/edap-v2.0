"""Common / landing / sql_instruments / Routine - step 04: Read from the source system.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "sql-loads/instruments"
STEP = {"order": 4, "name": "acquire_data", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.acquire_data(ctx)
