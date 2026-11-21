"""Commodities / consumption / exposure_metrics / Adhoc - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "exposure_metrics"
STEP = {"order": 1, "name": "init_context", "layer": "consumption", "mode": "Adhoc"}


def run(ctx):
    steps.init_context(ctx)
