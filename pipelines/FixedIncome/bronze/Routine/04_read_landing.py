"""FixedIncome / bronze / Routine - step 04: Read the landing files.

Routine mode: Auto Loader stream (availableNow): only new files.
"""
from edap_framework.pipeline import bronze_steps as steps

STEP = {"order": 4, "name": "read_landing", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.read_landing(ctx)
