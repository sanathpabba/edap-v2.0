"""FX / gold / trade_analytics / Adhoc - step 09: Write the run-log entry.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "trade_analytics"
STEP = {"order": 9, "name": "audit_log", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.audit_log(ctx)
