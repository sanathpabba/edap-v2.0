"""Landing: FX REST API -> JSON envelope in landing. Only the API source.
   python runners/landing_api.py --mode history --date 2026-11-16
   python runners/landing_api.py --mode daily   --date 2026-11-17"""
import argparse

import _bootstrap
from edap_framework.core import config
from edap_framework.ingestion.rest_api.fx_pull import land_fx

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["history", "daily"], required=True)
    ap.add_argument("--date", required=True, help="business date YYYY-MM-DD")
    ap.add_argument("--scenario", default=None)
    _bootstrap.add_run_id(ap)
    a = ap.parse_args()
    _bootstrap.apply_run_id(a)
    spark, env = _bootstrap.spark_session(), config.load_env()
    print("landed", land_fx(spark, config.load_spec("landing", "api-loads", "fx_rates"), env, a.mode, a.date, scenario=a.scenario))
