"""FX / bronze / stream_trade_events / Adhoc - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 1, "name": "init_context", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.init_context(ctx)
