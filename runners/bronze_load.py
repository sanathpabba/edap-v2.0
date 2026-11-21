"""Bronze: landing files -> Delta tables in edap.bronze. One source folder at a time, one table or all in it.
   python runners/bronze_load.py --source sql-loads [--table trades]
   python runners/bronze_load.py --source file-loads | stream-loads | api-loads"""
import argparse

import _bootstrap
from edap_framework.bronze.loader import load_bronze
from edap_framework.core import config

SOURCES = ["sql-loads", "file-loads", "stream-loads", "api-loads"]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=SOURCES, required=True)
    ap.add_argument("--table", help="omit for all tables of that source")
    ap.add_argument("--scenario", default=None)
    _bootstrap.add_run_id(ap)
    a = ap.parse_args()
    _bootstrap.apply_run_id(a)
    spark, env = _bootstrap.spark_session(), config.load_env()
    for t in ([a.table] if a.table else config.list_tables("bronze", a.source)):
        print(a.source, t, load_bronze(spark, config.load_spec("bronze", a.source, t), env, scenario=a.scenario,
                                              spec_path="definitions/bronze/%s/%s.yml" % (a.source, t)), "rows into bronze")
