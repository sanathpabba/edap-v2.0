"""Common / bronze / sql_instruments / Routine - step 06: Keep only this asset class's rows.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/instruments"
STEP = {"order": 6, "name": "route_to_asset_class", "layer": "bronze", "mode": "Routine"}


def run(ctx):
    steps.route_to_asset_class(ctx)
