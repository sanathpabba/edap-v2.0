"""FX / gold / Adhoc - step 05: Compose the product SQL from the YAML.
"""
from edap_framework.pipeline import gold_steps as steps

STEP = {"order": 5, "name": "compose_sql", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.compose_sql(ctx)
