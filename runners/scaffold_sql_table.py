"""Onboard a SQL table from its source-contract entry (landing + bronze + starter DQ specs).
   python runners/scaffold_sql_table.py --object source.trades [--overwrite]"""
import argparse

import _bootstrap  # noqa: F401
from edap_framework.ingestion.sql.scaffold import scaffold

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--object", required=True, help="e.g. reference.instruments")
    ap.add_argument("--source-file", default="definitions/sources/azure_sql_trading.yml")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    for f in scaffold(a.object, a.source_file, overwrite=a.overwrite) or ["(nothing written: files exist, use --overwrite)"]:
        print("wrote", f)
