"""Commodities / gold / pnl_finance / Routine - step 02: Read the data product definition.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "pnl_finance"
STEP = {"order": 2, "name": "read_product_yaml", "layer": "gold", "mode": "Routine"}


def run(ctx):
    steps.read_product_yaml(ctx)
