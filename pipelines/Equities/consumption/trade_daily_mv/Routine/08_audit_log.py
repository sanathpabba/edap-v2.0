"""Equities / consumption / trade_daily_mv / Routine - step 08: Write the run-log entry.
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "trade_daily_mv"
STEP = {"order": 8, "name": "audit_log", "layer": "consumption", "mode": "Routine"}


def run(ctx):
    steps.audit_log(ctx)
