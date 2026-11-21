"""Equities / bronze / file_positions / Routine - step 03: Resolve the asset-class routing rule and the replay window.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "file-loads/positions"
STEP = {"order": 3, "name": "resolve_scope", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.resolve_scope(ctx)
