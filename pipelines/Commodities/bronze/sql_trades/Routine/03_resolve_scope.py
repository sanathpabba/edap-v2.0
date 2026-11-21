"""Commodities / bronze / sql_trades / Routine - step 03: Resolve the asset-class routing rule and the replay window.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/trades"
STEP = {"order": 3, "name": "resolve_scope", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.resolve_scope(ctx)
