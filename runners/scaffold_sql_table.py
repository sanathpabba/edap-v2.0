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
    ap.add_argument("--route-column", help="instrument-key column to route rows to asset classes (e.g. sec_code); omit for shared tables")
    a = ap.parse_args()
    for f in scaffold(a.object, a.source_file, overwrite=a.overwrite, route_column=a.route_column) or ["(nothing written: files exist, use --overwrite)"]:
        print("wrote", f)
    print("Next: add 'sql-loads/<table>' to the landing and bronze item lists in definitions/asset_classes/common.yml "
          "(or to an asset class if the table is routed by instrument), then run runners/validate_definitions.py")
