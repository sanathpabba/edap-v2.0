"""FX / silver / instrument / Adhoc - step 08: DQ gate before the merge: halt only if the whole batch is wrong; email the owner on halt or warning.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "instrument"
STEP = {"order": 8, "name": "dq_gate_and_notify", "layer": "silver", "mode": "Adhoc"}


def run(ctx):
    steps.dq_gate_and_notify(ctx)
