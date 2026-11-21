"""FX / gold / position_exposure / Routine - step 05: Compose the product SQL from the YAML.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "position_exposure"
STEP = {"order": 5, "name": "compose_sql", "layer": "gold", "mode": "Routine"}


def run(ctx):
    steps.compose_sql(ctx)
