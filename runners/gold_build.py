"""Gold: build data products from product YAMLs (the conformed FX dimension first).
   python runners/gold_build.py [--product trade_analytics]"""
import argparse
import os

import _bootstrap
from edap_framework.core import config
from edap_framework.gold.builder import build_product

FIRST = ["fx_rate_daily"]

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--product"); ap.add_argument("--scenario"); _bootstrap.add_run_id(ap)
    a = ap.parse_args(); _bootstrap.apply_run_id(a)
    spark, env = _bootstrap.spark_session(), config.load_env()
    allp = sorted(f[:-4] for f in os.listdir(os.path.join(config.project_root(), "definitions", "gold_products")) if f.endswith(".yml"))
    for p in ([a.product] if a.product else FIRST + [x for x in allp if x not in FIRST]):
        print(p, build_product(spark, config.load_yaml("definitions/gold_products/%s.yml" % p), env, scenario=a.scenario))
