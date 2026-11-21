"""FX / bronze / stream_trade_events / Routine - step 04: Read the landing files.

Routine mode: Auto Loader stream (availableNow): only new files.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 4, "name": "read_landing", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.read_landing(ctx)
