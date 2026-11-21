"""Common / bronze / sql_counterparties / Routine - step 03: Resolve the asset-class routing rule and the replay window.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/counterparties"
STEP = {"order": 3, "name": "resolve_scope", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.resolve_scope(ctx)
