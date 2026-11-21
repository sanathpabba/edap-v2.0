"""Commodities / silver / trade / Adhoc - step 10: MERGE into the canonical table, advance the watermark, tag, log.

Adhoc mode: The watermark only moves forward.
"""
from edap_framework.pipeline import silver_steps as steps

ITEM = "trade"
STEP = {"order": 10, "name": "merge_and_finalize", "layer": "silver", "mode": "Adhoc"}


def run(ctx):
    steps.merge_and_finalize(ctx)
