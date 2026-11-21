"""FX / consumption / exposure_metrics / Routine - step 07: Prove it works: a MEASURE() query or a row count.
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "exposure_metrics"
STEP = {"order": 7, "name": "verify_object", "layer": "consumption", "mode": "Routine"}


def run(ctx):
    steps.verify_object(ctx)
