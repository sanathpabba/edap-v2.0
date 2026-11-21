"""Common / landing / sql_instruments / Routine - step 08: Write the run-log entry.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "sql-loads/instruments"
STEP = {"order": 8, "name": "audit_log", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.audit_log(ctx)
