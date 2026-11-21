"""Equities / gold / position_exposure / Routine - step 06: Execute the SQL and write the Gold table.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "position_exposure"
STEP = {"order": 6, "name": "build_and_write", "layer": "gold", "mode": "Routine"}


def run(ctx):
    steps.build_and_write(ctx)
