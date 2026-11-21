"""DQX at Bronze: check every unchecked Bronze batch, quarantine bad rows, record results. One source folder at a time.
   python runners/dq_bronze.py --source file-loads [--table positions]"""
import argparse

import _bootstrap
from edap_framework.core import config
from edap_framework.dq.bronze_check import check_bronze_table
from edap_framework.dq.quarantine import close_superseded_by_resend

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["sql-loads", "file-loads", "stream-loads", "api-loads"], required=True)
    ap.add_argument("--table"); _bootstrap.add_run_id(ap)
    a = ap.parse_args(); _bootstrap.apply_run_id(a)
    spark, env = _bootstrap.spark_session(), config.load_env()
    for t in ([a.table] if a.table else config.list_tables("bronze", a.source)):
        spec = config.load_spec("bronze", a.source, t)
        print(a.source, t, check_bronze_table(spark, spec, env))
        if a.source == "file-loads":                       # a corrected resend closes the quarantined rows of the earlier version
            close_superseded_by_resend(spark, env, "%s.%s.%s" % (spec["target"]["catalog"], spec["target"]["schema"], spec["target"]["table"]))
