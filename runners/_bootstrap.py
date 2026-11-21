"""Shared runner start-up: make edap_framework importable and create the Spark session."""
import os
import sys

ROOT = os.environ.get("EDAP_PROJECT_ROOT") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("EDAP_PROJECT_ROOT", ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def spark_session():
    from pyspark.sql import SparkSession
    return SparkSession.builder.getOrCreate()


def add_run_id(ap):
    """Every runner accepts --run-id (jobs pass {{job.run_id}}); it is stamped on run-log rows and Bronze rows."""
    ap.add_argument("--run-id", default=None, help="Databricks job run id for lineage")


def apply_run_id(args):
    if args.run_id:
        os.environ["EDAP_RUN_ID"] = str(args.run_id)
