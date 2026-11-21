"""Equities / bronze / file_positions / Adhoc - step 10: Run DQX at Bronze, close superseded quarantine rows, write the run log.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "file-loads/positions"
STEP = {"order": 10, "name": "run_dq_and_audit", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.run_dq_and_audit(ctx)
