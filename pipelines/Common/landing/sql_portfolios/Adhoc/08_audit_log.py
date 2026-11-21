"""Common / landing / sql_portfolios / Adhoc - step 08: Write the run-log entry.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "sql-loads/portfolios"
STEP = {"order": 8, "name": "audit_log", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.audit_log(ctx)
