"""Equities / consumption / trade_metrics / Routine - step 08: Write the run-log entry.
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "trade_metrics"
STEP = {"order": 8, "name": "audit_log", "layer": "consumption", "mode": "Routine"}


def run(ctx):
    steps.audit_log(ctx)
