"""FixedIncome / bronze / file_positions / Adhoc - step 03: Resolve the asset-class routing rule and the replay window.

Adhoc mode: Replay window from --from-ts / --to-ts.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "file-loads/positions"
STEP = {"order": 3, "name": "resolve_scope", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.resolve_scope(ctx)
