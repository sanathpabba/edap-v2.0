"""Common / landing / stream_trade_events / Adhoc - step 05: Whole-file checks (received? readable? right header? not empty?); a wrong file is rejected and the owner emailed.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 5, "name": "validate_batch", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.validate_batch(ctx)
