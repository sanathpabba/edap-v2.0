"""Common / landing / file_positions / Adhoc - step 08: Advance the SQL watermark after a successful write.

Adhoc mode: Only moves forward; an Adhoc backfill never lowers it.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "file-loads/positions"
STEP = {"order": 8, "name": "advance_watermark", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.advance_watermark(ctx)
