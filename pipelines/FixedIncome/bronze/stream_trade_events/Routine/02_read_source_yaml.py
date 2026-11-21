"""FixedIncome / bronze / stream_trade_events / Routine - step 02: Read the Bronze spec, landing spec and source contract.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 2, "name": "read_source_yaml", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.read_source_yaml(ctx)
