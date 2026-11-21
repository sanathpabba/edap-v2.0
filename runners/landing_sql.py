"""Landing: Azure SQL -> Parquet in landing. Only the SQL source; one table or all SQL tables.
   python runners/landing_sql.py [--table trades] [--scenario d0]"""
import argparse

import _bootstrap
from edap_framework.core import config
from edap_framework.ingestion.sql.extract import land_table

SRC = "sql-loads"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", help="one table name; omit for all tables under definitions/landing/sql-loads")
    ap.add_argument("--scenario", default=None, help="label for the run log (d0/d1/d2)")
    _bootstrap.add_run_id(ap)
    a = ap.parse_args()
    _bootstrap.apply_run_id(a)
    spark, env = _bootstrap.spark_session(), config.load_env()
    for t in ([a.table] if a.table else config.list_tables("landing", SRC)):
        print(t, land_table(spark, config.load_spec("landing", SRC, t), env, scenario=a.scenario), "rows landed")
