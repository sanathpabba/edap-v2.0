"""Equities / bronze / file_positions / Adhoc - step 04: Read the landing files.

Adhoc mode: Batch read of landing files in the replay window.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "file-loads/positions"
STEP = {"order": 4, "name": "read_landing", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.read_landing(ctx)
