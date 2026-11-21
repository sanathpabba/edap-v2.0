"""FX / gold / regulatory_reporting / Adhoc - step 08: Run DQX sanity checks (flag mode).
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "regulatory_reporting"
STEP = {"order": 8, "name": "run_expectations", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.run_expectations(ctx)
