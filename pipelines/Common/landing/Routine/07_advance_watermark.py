"""Common / landing / Routine - step 07: Advance the SQL watermark after a successful write.
"""
from edap_framework.pipeline import landing_steps as steps

STEP = {"order": 7, "name": "advance_watermark", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.advance_watermark(ctx)
