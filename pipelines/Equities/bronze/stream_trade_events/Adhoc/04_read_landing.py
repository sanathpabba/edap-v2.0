"""Equities / bronze / stream_trade_events / Adhoc - step 04: Read the landing files.

Adhoc mode: Batch read of landing files in the replay window.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 4, "name": "read_landing", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.read_landing(ctx)
