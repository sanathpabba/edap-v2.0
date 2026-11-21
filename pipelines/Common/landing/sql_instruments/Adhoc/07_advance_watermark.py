"""Common / landing / sql_instruments / Adhoc - step 07: Advance the SQL watermark after a successful write.

Adhoc mode: Only moves forward; an Adhoc backfill never lowers it.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "sql-loads/instruments"
STEP = {"order": 7, "name": "advance_watermark", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.advance_watermark(ctx)
