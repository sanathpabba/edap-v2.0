"""Common / gold / fx_rate_daily / Adhoc - step 05: Compose the product SQL from the YAML.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "fx_rate_daily"
STEP = {"order": 5, "name": "compose_sql", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.compose_sql(ctx)
