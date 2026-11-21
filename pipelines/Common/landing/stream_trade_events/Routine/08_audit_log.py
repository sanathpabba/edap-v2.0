"""Common / landing / stream_trade_events / Routine - step 08: Write the run-log entry.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 8, "name": "audit_log", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.audit_log(ctx)
