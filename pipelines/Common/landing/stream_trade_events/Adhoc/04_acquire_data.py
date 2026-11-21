"""Common / landing / stream_trade_events / Adhoc - step 04: Read from the source system.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 4, "name": "acquire_data", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.acquire_data(ctx)
