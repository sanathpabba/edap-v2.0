"""Commodities / bronze / Adhoc - step 01: Initialise the run: schemas, run id, clock.
"""
from edap_framework.pipeline import bronze_steps as steps

STEP = {"order": 1, "name": "init_context", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.init_context(ctx)
