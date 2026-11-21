"""FixedIncome / consumption / exposure_metrics / Routine - step 03: Check the Gold product it reads exists.
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "exposure_metrics"
STEP = {"order": 3, "name": "check_upstream", "layer": "consumption", "mode": "Routine"}


def run(ctx):
    steps.check_upstream(ctx)
