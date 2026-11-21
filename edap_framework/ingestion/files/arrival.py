"""Landing for file sources: register every file that arrived in landing/<x>/inbound (content is never altered)."""
import datetime as dt
import re

from edap_framework.core import audit, config, spark_utils

REG_DDL = """CREATE TABLE IF NOT EXISTS {t} (
  file_name STRING, file_path STRING, size_bytes BIGINT, business_date STRING, version INT,
  arrived_ts TIMESTAMP, registered_ts TIMESTAMP, batch_id STRING, status STRING)"""


def register_arrivals(spark, spec, env, batch_id=None, scenario=None):
    batch_id = batch_id or audit.new_batch_id()
    started = dt.datetime.utcnow()
    arr = spec["arrival"]
    reg = spec["registry"]["table"]
    spark.sql(REG_DDL.format(t=reg))
    dbu = spark_utils.get_dbutils(spark)
    folder = config.storage_uri(env, arr["container"], arr["inbound_path"])
    pat = re.compile(arr["file_pattern"])
    known = {(r[0], r[1]) for r in spark.sql("SELECT file_name, size_bytes FROM %s" % reg).collect()}
    rows = []
    for f in dbu.fs.ls(folder):
        if f.isDir():
            continue
        m = pat.match(f.name)
        if (f.name, f.size) in known:
            continue                                   # duplicate_file_rule: skip_if_same_name_and_size
        bdate = m.group(arr["business_date_group"]) if m else None
        ver = int(m.group(arr["version_group"]) or 1) if m else None
        rows.append((f.name, f.path, f.size, bdate, ver, dt.datetime.utcfromtimestamp(f.modificationTime / 1000.0),
                     dt.datetime.utcnow(), batch_id, "REGISTERED" if m else "UNRECOGNISED_NAME"))
    if rows:
        spark.createDataFrame(rows, "file_name string, file_path string, size_bytes long, business_date string, version int, "
                                    "arrived_ts timestamp, registered_ts timestamp, batch_id string, status string") \
             .write.mode("append").saveAsTable(reg)
    audit.log_run(spark, spec["audit"]["run_log"], batch_id=batch_id, layer="landing", source_system=spec["source_system"],
                  table_name=spec["table"], scenario=scenario, status="SUCCESS", rows_processed=len(rows),
                  started_ts=started, finished_ts=dt.datetime.utcnow(), details="%d new file(s) registered" % len(rows))
    return len(rows)
