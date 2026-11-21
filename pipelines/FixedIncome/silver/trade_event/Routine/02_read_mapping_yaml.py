"""FixedIncome / silver / trade_event / Routine - step 02: Read the canonical mapping for the entity.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "trade_event"
STEP = {"order": 2, "name": "read_mapping_yaml", "layer": "silver", "mode": "Routine"}


def run(ctx):
    steps.read_mapping_yaml(ctx)
