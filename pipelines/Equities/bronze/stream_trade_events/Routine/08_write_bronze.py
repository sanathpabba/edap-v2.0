"""Equities / bronze / stream_trade_events / Routine - step 08: Write the Bronze Delta table and apply Unity Catalog comment and tags.

Routine mode: Streaming append with checkpoint.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 8, "name": "write_bronze", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.write_bronze(ctx)
