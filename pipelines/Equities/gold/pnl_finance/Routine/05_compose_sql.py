"""Equities / gold / pnl_finance / Routine - step 05: Compose the product SQL from the YAML.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "pnl_finance"
STEP = {"order": 5, "name": "compose_sql", "layer": "gold", "mode": "Routine"}


def run(ctx):
    steps.compose_sql(ctx)
