"""Equities / gold / position_exposure / Routine - step 03: Resolve product parameters.

Routine mode: YAML defaults.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "position_exposure"
STEP = {"order": 3, "name": "resolve_parameters", "layer": "gold", "mode": "Routine"}


def run(ctx):
    steps.resolve_parameters(ctx)
