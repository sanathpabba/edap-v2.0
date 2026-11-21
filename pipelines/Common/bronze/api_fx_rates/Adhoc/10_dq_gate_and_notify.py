"""Common / bronze / api_fx_rates / Adhoc - step 10: DQ gate: halt only if the whole batch is wrong; email the owner on halt or warning; write the run log.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "api-loads/fx_rates"
STEP = {"order": 10, "name": "dq_gate_and_notify", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.dq_gate_and_notify(ctx)
