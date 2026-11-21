"""FixedIncome / consumption / trade_metrics / Routine - step 05: Run the statement (job compute or the configured SQL warehouse).
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "trade_metrics"
STEP = {"order": 5, "name": "create_or_refresh", "layer": "consumption", "mode": "Routine"}


def run(ctx):
    steps.create_or_refresh(ctx)
