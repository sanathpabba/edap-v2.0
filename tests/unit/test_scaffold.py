import os
import shutil

from edap_framework.core import config
from edap_framework.ingestion.sql.scaffold import scaffold

TABLES = ["reference.instruments", "reference.portfolios", "reference.accounts", "reference.counterparties", "source.trades"]


def test_scaffold_reproduces_existing_specs(tmp_path):
    for obj in TABLES:
        written = scaffold(obj, root=str(tmp_path))
        assert len(written) == 3
        for rel in written[:2]:                                       # landing + bronze
            mine = __import__("yaml").safe_load(open(tmp_path / rel))
            old = config.load_yaml(rel)
            assert mine == old, rel


def test_scaffold_does_not_overwrite(tmp_path):
    scaffold("reference.instruments", root=str(tmp_path))
    assert scaffold("reference.instruments", root=str(tmp_path)) == []
