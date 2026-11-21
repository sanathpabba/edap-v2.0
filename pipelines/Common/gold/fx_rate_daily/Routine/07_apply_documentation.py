"""Common / gold / fx_rate_daily / Routine - step 07: Apply purpose, grain, owner, refresh as comment and tags.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "fx_rate_daily"
STEP = {"order": 7, "name": "apply_documentation", "layer": "gold", "mode": "Routine"}


def run(ctx):
    steps.apply_documentation(ctx)
