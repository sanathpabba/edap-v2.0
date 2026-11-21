"""FixedIncome / silver / instrument / Routine - step 08: Run DQX business rules, quarantine invalid rows.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "instrument"
STEP = {"order": 8, "name": "run_dq_silver", "layer": "silver", "mode": "Routine"}


def run(ctx):
    steps.run_dq_silver(ctx)
