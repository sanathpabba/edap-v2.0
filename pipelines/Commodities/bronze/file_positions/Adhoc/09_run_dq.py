"""Commodities / bronze / file_positions / Adhoc - step 09: Run DQX at Bronze, quarantine failing rows, close rows superseded by a corrected file.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "file-loads/positions"
STEP = {"order": 9, "name": "run_dq", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.run_dq(ctx)
