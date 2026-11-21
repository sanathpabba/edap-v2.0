"""Common / bronze / sql_accounts / Adhoc - step 09: Apply Unity Catalog comment and tags.
"""
from edap_framework.pipeline import bronze_steps as steps

ITEM = "sql-loads/accounts"
STEP = {"order": 9, "name": "apply_governance", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.apply_governance(ctx)
