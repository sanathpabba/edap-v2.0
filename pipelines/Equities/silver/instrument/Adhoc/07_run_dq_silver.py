"""Equities / silver / instrument / Adhoc - step 07: Run DQX business rules, quarantine invalid rows.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "instrument"
STEP = {"order": 7, "name": "run_dq_silver", "layer": "silver", "mode": "Adhoc"}


def run(ctx):
    steps.run_dq_silver(ctx)
