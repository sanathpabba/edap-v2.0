"""Common / silver / portfolio / Adhoc - step 03: Read new Bronze rows, minus DQ-quarantined rows.

Adhoc mode: Since --from-ts, or everything (full rebuild).
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "portfolio"
STEP = {"order": 3, "name": "read_bronze_increment", "layer": "silver", "mode": "Adhoc"}


def run(ctx):
    steps.read_bronze_increment(ctx)
