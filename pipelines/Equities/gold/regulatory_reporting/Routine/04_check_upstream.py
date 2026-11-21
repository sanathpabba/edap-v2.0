"""Equities / gold / regulatory_reporting / Routine - step 04: Check upstream tables exist and are not empty.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "regulatory_reporting"
STEP = {"order": 4, "name": "check_upstream", "layer": "gold", "mode": "Routine"}


def run(ctx):
    steps.check_upstream(ctx)
