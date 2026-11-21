"""FX / consumption / trade_metrics / Adhoc - step 06: Apply purpose, grain, owner, refresh as tags (best effort).
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "trade_metrics"
STEP = {"order": 6, "name": "apply_documentation", "layer": "consumption", "mode": "Adhoc"}


def run(ctx):
    steps.apply_documentation(ctx)
