"""Common / landing / stream_trade_events / Routine - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 1, "name": "init_context", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.init_context(ctx)
