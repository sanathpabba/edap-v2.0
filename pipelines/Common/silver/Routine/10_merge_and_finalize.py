"""Common / silver / Routine - step 10: MERGE into the canonical table, advance the watermark, tag, log.
"""
from edap_framework.pipeline import silver_steps as steps

STEP = {"order": 10, "name": "merge_and_finalize", "layer": "silver", "mode": "Routine"}


def run(ctx):
    steps.merge_and_finalize(ctx)
