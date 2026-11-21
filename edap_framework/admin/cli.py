"""Console command `edap-admin`: platform administration (run on Databricks, e.g. from a notebook or job).
  edap-admin reset --dry-run     list what a reset would drop and delete
  edap-admin reset --yes         do it (destructive: pipeline tables, run state, landing files, checkpoints)"""
import argparse
import sys

from edap_framework.admin.reset import reset_platform
from edap_framework.core import config, spark_utils


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["reset"])
    ap.add_argument("--yes", action="store_true", help="confirm the destructive reset")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.getOrCreate()
    out = reset_platform(spark, spark_utils.get_dbutils(spark), config.load_env(), confirm=a.yes, dry_run=a.dry_run)
    return 1 if out.get("failed") else 0


if __name__ == "__main__":
    sys.exit(main())
