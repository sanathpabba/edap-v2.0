"""Landing: Event Hubs -> raw JSON files in landing (drains what is in the hub, then stops). Only the event source.
   python runners/landing_stream.py [--namespace edap-eventhubs-645ca5]"""
import argparse

import _bootstrap
from edap_framework.core import config
from edap_framework.ingestion.streaming.eventhub_to_landing import land_events

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--namespace", default="edap-eventhubs-645ca5")
    ap.add_argument("--scenario", default=None)
    _bootstrap.add_run_id(ap)
    a = ap.parse_args()
    _bootstrap.apply_run_id(a)
    spark, env = _bootstrap.spark_session(), config.load_env()
    print(land_events(spark, config.load_spec("landing", "stream-loads", "trade_events"), env, a.namespace, scenario=a.scenario), "events landed")
