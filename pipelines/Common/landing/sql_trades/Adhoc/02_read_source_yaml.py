"""Common / landing / sql_trades / Adhoc - step 02: Read the landing spec and the source contract.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "sql-loads/trades"
STEP = {"order": 2, "name": "read_source_yaml", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.read_source_yaml(ctx)
