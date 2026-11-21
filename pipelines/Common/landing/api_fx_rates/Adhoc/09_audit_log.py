"""Common / landing / api_fx_rates / Adhoc - step 09: Write the run-log entry; halt the pipeline if a whole file was missing or wrong.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "api-loads/fx_rates"
STEP = {"order": 9, "name": "audit_log", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.audit_log(ctx)
