"""Commodities / silver / trade_event / Adhoc - step 04: Read new Bronze rows, minus DQ-quarantined rows.

Adhoc mode: Since --from-ts, or everything (full rebuild).
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "trade_event"
STEP = {"order": 4, "name": "read_bronze_increment", "layer": "silver", "mode": "Adhoc"}


def run(ctx):
    steps.read_bronze_increment(ctx)
