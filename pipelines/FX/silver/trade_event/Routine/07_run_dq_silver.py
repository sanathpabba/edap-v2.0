"""FX / silver / trade_event / Routine - step 07: Run DQX business rules, quarantine invalid rows.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "trade_event"
STEP = {"order": 7, "name": "run_dq_silver", "layer": "silver", "mode": "Routine"}


def run(ctx):
    steps.run_dq_silver(ctx)
