"""Commodities / consumption / portfolio_exposure_mv / Routine - step 04: Compose CREATE ... WITH METRICS, or CREATE / REFRESH MATERIALIZED VIEW.

Routine mode: Materialized views are refreshed when they exist.
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "portfolio_exposure_mv"
STEP = {"order": 4, "name": "compose_sql", "layer": "consumption", "mode": "Routine"}


def run(ctx):
    steps.compose_sql(ctx)
