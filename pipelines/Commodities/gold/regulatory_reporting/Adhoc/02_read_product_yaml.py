"""Commodities / gold / regulatory_reporting / Adhoc - step 02: Read the data product definition.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "regulatory_reporting"
STEP = {"order": 2, "name": "read_product_yaml", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.read_product_yaml(ctx)
