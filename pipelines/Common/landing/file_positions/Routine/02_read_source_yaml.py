"""Common / landing / file_positions / Routine - step 02: Read the landing spec and the source contract.
"""
from edap_framework.pipeline import landing_steps as steps

ITEM = "file-loads/positions"
STEP = {"order": 2, "name": "read_source_yaml", "layer": "landing", "mode": "Routine"}


def run(ctx):
    steps.read_source_yaml(ctx)
