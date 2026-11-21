"""Common / landing / sql_portfolios / Routine - step 08: Advance the SQL watermark after a successful write.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "sql-loads/portfolios"
STEP = {"order": 8, "name": "advance_watermark", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.advance_watermark(ctx)
