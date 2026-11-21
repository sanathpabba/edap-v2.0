"""FixedIncome / consumption / portfolio_exposure_mv / Routine - step 07: Prove it works: a MEASURE() query or a row count.
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "portfolio_exposure_mv"
STEP = {"order": 7, "name": "verify_object", "layer": "consumption", "mode": "Routine"}


def run(ctx):
    steps.verify_object(ctx)
