"""FX / bronze / stream_trade_events / Routine - step 10: Run DQX at Bronze, close superseded quarantine rows, write the run log.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 10, "name": "run_dq_and_audit", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.run_dq_and_audit(ctx)
