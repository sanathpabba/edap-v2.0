"""Commodities / consumption / portfolio_exposure_mv / Adhoc - step 05: Run the statement (job compute or the configured SQL warehouse).
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "portfolio_exposure_mv"
STEP = {"order": 5, "name": "create_or_refresh", "layer": "consumption", "mode": "Adhoc"}


def run(ctx):
    steps.create_or_refresh(ctx)
