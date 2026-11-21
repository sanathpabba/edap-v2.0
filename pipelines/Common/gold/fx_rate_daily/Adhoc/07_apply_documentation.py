"""Common / gold / fx_rate_daily / Adhoc - step 07: Apply purpose, grain, owner, refresh as comment and tags.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "fx_rate_daily"
STEP = {"order": 7, "name": "apply_documentation", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.apply_documentation(ctx)
