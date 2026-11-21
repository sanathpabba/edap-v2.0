"""Equities / bronze / stream_trade_events / Adhoc - step 08: Write the Bronze Delta table.

Adhoc mode: Delete the replayed landing batches, then append: no duplicates.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 8, "name": "write_bronze", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.write_bronze(ctx)
