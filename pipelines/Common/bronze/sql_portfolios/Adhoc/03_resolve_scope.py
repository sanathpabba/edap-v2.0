"""Common / bronze / sql_portfolios / Adhoc - step 03: Resolve the asset-class routing rule and the replay window.

Adhoc mode: Replay window from --from-ts / --to-ts.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/portfolios"
STEP = {"order": 3, "name": "resolve_scope", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.resolve_scope(ctx)
