"""Landing: register position files that arrived in landing/positions/inbound. Only the file source.
   python runners/landing_files.py [--scenario d0]"""
import argparse

import _bootstrap
from edap_framework.core import config
from edap_framework.ingestion.files.arrival import register_arrivals

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default=None)
    _bootstrap.add_run_id(ap)
    a = ap.parse_args()
    _bootstrap.apply_run_id(a)
    spark, env = _bootstrap.spark_session(), config.load_env()
    print(register_arrivals(spark, config.load_spec("landing", "file-loads", "positions"), env, scenario=a.scenario), "new file(s) registered")
