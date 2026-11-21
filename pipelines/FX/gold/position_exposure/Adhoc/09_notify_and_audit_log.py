"""FX / gold / position_exposure / Adhoc - step 09: Email the owner the failed sanity checks (if any); write the run-log entry.
"""
from edap_framework.pipeline import gold_steps as steps

ITEM = "position_exposure"
STEP = {"order": 9, "name": "notify_and_audit_log", "layer": "gold", "mode": "Adhoc"}


def run(ctx):
    steps.notify_and_audit_log(ctx)
