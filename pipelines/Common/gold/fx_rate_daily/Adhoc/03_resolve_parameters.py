"""Common / gold / fx_rate_daily / Adhoc - step 03: Resolve product parameters.

Adhoc mode: YAML defaults overridden by --param name=value (what-if runs).
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "fx_rate_daily"
STEP = {"order": 3, "name": "resolve_parameters", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.resolve_parameters(ctx)
