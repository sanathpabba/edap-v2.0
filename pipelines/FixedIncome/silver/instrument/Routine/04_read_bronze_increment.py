"""FixedIncome / silver / instrument / Routine - step 04: Read new Bronze rows, minus DQ-quarantined rows.

Routine mode: Since the Silver watermark.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "instrument"
STEP = {"order": 4, "name": "read_bronze_increment", "layer": "silver", "mode": "Routine"}


def run(ctx):
    steps.read_bronze_increment(ctx)
