"""FixedIncome / consumption / exposure_metrics / Adhoc - step 04: Compose CREATE ... WITH METRICS, or CREATE / REFRESH MATERIALIZED VIEW.

Adhoc mode: --extra rebuild=true recreates a materialized view (use after changing its SELECT).
"""
from edap_framework.pipeline import consumption_steps as steps

ITEM = "exposure_metrics"
STEP = {"order": 4, "name": "compose_sql", "layer": "consumption", "mode": "Adhoc"}


def run(ctx):
    steps.compose_sql(ctx)
