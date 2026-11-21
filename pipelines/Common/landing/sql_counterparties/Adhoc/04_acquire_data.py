"""Common / landing / sql_counterparties / Adhoc - step 04: Read from the source system.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "sql-loads/counterparties"
STEP = {"order": 4, "name": "acquire_data", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.acquire_data(ctx)
