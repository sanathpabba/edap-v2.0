"""FX / bronze / stream_trade_events / Routine - step 05: Apply the spec's shaping (JSON extract, payload parse, extra columns).
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 5, "name": "shape_columns", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.shape_columns(ctx)
