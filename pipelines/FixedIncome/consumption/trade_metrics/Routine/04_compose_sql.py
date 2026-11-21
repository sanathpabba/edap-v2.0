"""FixedIncome / consumption / trade_metrics / Routine - step 04: Compose CREATE ... WITH METRICS, or CREATE / REFRESH MATERIALIZED VIEW.

Routine mode: Materialized views are refreshed when they exist.
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "trade_metrics"
STEP = {"order": 4, "name": "compose_sql", "layer": "consumption", "mode": "Routine"}


def run(ctx):
    steps.compose_sql(ctx)
