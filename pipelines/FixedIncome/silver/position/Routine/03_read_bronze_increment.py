"""FixedIncome / silver / position / Routine - step 03: Read new Bronze rows, minus DQ-quarantined rows.

Routine mode: Since the Silver watermark.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "position"
STEP = {"order": 3, "name": "read_bronze_increment", "layer": "silver", "mode": "Routine"}


def run(ctx):
    steps.read_bronze_increment(ctx)
