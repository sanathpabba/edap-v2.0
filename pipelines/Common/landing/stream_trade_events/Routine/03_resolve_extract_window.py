"""Common / landing / stream_trade_events / Routine - step 03: Decide what to fetch (watermark window, FX date, expected file, event offsets).

Routine mode: SQL: stored watermark .. current max. FX: today's daily rates. Files: new files in the source drop.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 3, "name": "resolve_extract_window", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.resolve_extract_window(ctx)
