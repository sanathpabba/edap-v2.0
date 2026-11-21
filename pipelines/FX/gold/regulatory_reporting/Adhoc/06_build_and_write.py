"""FX / gold / regulatory_reporting / Adhoc - step 06: Execute the SQL and write the Gold table.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "regulatory_reporting"
STEP = {"order": 6, "name": "build_and_write", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.build_and_write(ctx)
