"""FX / bronze / stream_trade_events / Adhoc - step 03: Resolve the asset-class routing rule and the replay window.

Adhoc mode: Replay window from --from-ts / --to-ts.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "stream-loads/trade_events"
STEP = {"order": 3, "name": "resolve_scope", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.resolve_scope(ctx)
