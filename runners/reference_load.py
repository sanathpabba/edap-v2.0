"""Load governed reference data (definitions/reference_data/*.yml) into edap.reference.*   python runners/reference_load.py [--name currency]"""
import argparse

import _bootstrap
from edap_framework.core import config
from edap_framework.silver.reference import list_reference, load_reference

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--name"); _bootstrap.add_run_id(ap)
    a = ap.parse_args(); _bootstrap.apply_run_id(a)
    spark, env = _bootstrap.spark_session(), config.load_env()
    for n in ([a.name] if a.name else list_reference()):
        print(n, load_reference(spark, n, env), "rows loaded")
