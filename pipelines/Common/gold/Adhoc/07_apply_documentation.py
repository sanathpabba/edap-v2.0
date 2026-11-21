"""Common / gold / Adhoc - step 07: Apply purpose, grain, owner, refresh as comment and tags.
"""
from edap_framework.pipeline import gold_steps as steps

STEP = {"order": 7, "name": "apply_documentation", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.apply_documentation(ctx)
