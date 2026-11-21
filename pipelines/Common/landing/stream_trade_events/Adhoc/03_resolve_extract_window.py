"""Common / landing / stream_trade_events / Adhoc - step 03: Decide what to fetch (watermark window, FX date, expected file, event offsets).

Adhoc mode: SQL: --from-ts or a full re-extract. FX: history. Files: --rescan re-checks files already seen. Events: replay from the earliest offset.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 3, "name": "resolve_extract_window", "layer": "landing", "mode": "Adhoc"}


def run(ctx):
    steps.resolve_extract_window(ctx)
