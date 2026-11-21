"""Batch ids and the ingestion run log (edap.audit.ingestion_runs). Every landing/bronze run writes one row."""
import datetime as dt
import os
import uuid

RUN_LOG_DDL = """CREATE TABLE IF NOT EXISTS {t} (
  batch_id STRING, run_id STRING, layer STRING, source_system STRING, table_name STRING, scenario STRING,
  status STRING, rows_processed BIGINT, started_ts TIMESTAMP, finished_ts TIMESTAMP, details STRING)"""


def run_id():
    """Databricks job run id (passed by the job as --run-id {{job.run_id}}); 'manual' when run by hand."""
    return os.environ.get("EDAP_RUN_ID") or "manual"


def new_batch_id():
    return dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]


def log_run(spark, run_log_table, **row):
    spark.sql(RUN_LOG_DDL.format(t=run_log_table))
    cols = ["batch_id", "run_id", "layer", "source_system", "table_name", "scenario", "status", "rows_processed", "started_ts", "finished_ts", "details"]
    r = {c: row.get(c) for c in cols}
    r["run_id"] = r["run_id"] or run_id()
    df = spark.createDataFrame([(r["batch_id"], r["run_id"], r["layer"], r["source_system"], r["table_name"], r["scenario"], r["status"],
                                 r["rows_processed"], r["started_ts"], r["finished_ts"], r["details"])],
                               "batch_id string, run_id string, layer string, source_system string, table_name string, scenario string, status string, "
                               "rows_processed long, started_ts timestamp, finished_ts timestamp, details string")
    df.write.mode("append").saveAsTable(run_log_table)
