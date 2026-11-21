"""Equities / bronze / stream_trade_events / Adhoc - step 07: Add audit and lineage columns.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 7, "name": "add_meta_properties", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.add_meta_properties(ctx)
