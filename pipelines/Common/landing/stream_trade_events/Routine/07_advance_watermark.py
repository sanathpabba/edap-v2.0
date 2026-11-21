"""Common / landing / stream_trade_events / Routine - step 07: Advance the SQL watermark after a successful write.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 7, "name": "advance_watermark", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.advance_watermark(ctx)
