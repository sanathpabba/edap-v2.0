"""Equities / consumption / trade_metrics / Adhoc - step 05: Run the statement (job compute or the configured SQL warehouse).
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "trade_metrics"
STEP = {"order": 5, "name": "create_or_refresh", "layer": "consumption", "mode": "Adhoc"}


def run(ctx):
    steps.create_or_refresh(ctx)
