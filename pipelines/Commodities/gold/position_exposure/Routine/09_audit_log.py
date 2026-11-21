"""Commodities / gold / position_exposure / Routine - step 09: Write the run-log entry.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "position_exposure"
STEP = {"order": 9, "name": "audit_log", "layer": "gold", "mode": "Routine"}


def run(ctx):
    steps.audit_log(ctx)
