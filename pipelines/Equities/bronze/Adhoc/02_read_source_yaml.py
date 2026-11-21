"""Equities / bronze / Adhoc - step 02: Read the Bronze spec, landing spec and source contract.
"""
from edap_framework.pipeline import bronze_steps as steps

STEP = {"order": 2, "name": "read_source_yaml", "layer": "bronze", "mode": "Adhoc"}


def run(ctx):
    steps.read_source_yaml(ctx)
