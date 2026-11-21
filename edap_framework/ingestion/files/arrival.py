"""Landing for file sources, as small functions: scan_arrivals -> register_arrivals (content is never altered)."""
import datetime as dt
import re

from edap_framework.core import config, spark_utils

REG_DDL = """CREATE TABLE IF NOT EXISTS {t} (
  file_name STRING, file_path STRING, size_bytes BIGINT, business_date STRING, version INT,
  arrived_ts TIMESTAMP, registered_ts TIMESTAMP, batch_id STRING, status STRING)"""
REG_SCHEMA = ("file_name string, file_path string, size_bytes long, business_date string, version int, "
              "arrived_ts timestamp, registered_ts timestamp, batch_id string, status string")


def scan_arrivals(spark, spec, env, batch_id, rescan=False):
    """New files in the inbound folder (same name + size already registered are skipped unless rescan=True)."""
    arr, reg = spec["arrival"], spec["registry"]["table"]
    spark.sql(REG_DDL.format(t=reg))
    known = set() if rescan else {(r[0], r[1]) for r in spark.sql("SELECT file_name, size_bytes FROM %s" % reg).collect()}
    pat, rows = re.compile(arr["file_pattern"]), []
    for f in spark_utils.get_dbutils(spark).fs.ls(config.storage_uri(env, arr["container"], arr["inbound_path"])):
        if f.isDir() or (f.name, f.size) in known:
            continue
        m = pat.match(f.name)
        rows.append((f.name, f.path, f.size, m.group(arr["business_date_group"]) if m else None,
                     int(m.group(arr["version_group"]) or 1) if m else None,
                     dt.datetime.utcfromtimestamp(f.modificationTime / 1000.0), dt.datetime.utcnow(), batch_id,
                     "REGISTERED" if m else "UNRECOGNISED_NAME"))
    return rows


def register_arrivals(spark, spec, rows):
    if rows:
        spark.createDataFrame(rows, REG_SCHEMA).write.mode("append").saveAsTable(spec["registry"]["table"])
    return len(rows)
