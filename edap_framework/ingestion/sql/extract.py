"""Landing for relational sources: JDBC extract (full on first run, watermark delta afterwards) -> Parquet in landing."""
import datetime as dt

from edap_framework.core import audit, config, spark_utils
from edap_framework.metadata import watermarks


def _jdbc_url(spark, env):
    server = spark_utils.secret(spark, env, "sql_server")
    db = spark_utils.secret(spark, env, "sql_database")
    return "jdbc:sqlserver://%s.database.windows.net:1433;database=%s;encrypt=true;loginTimeout=30" % (server.split(".")[0], db)


def land_table(spark, spec, env, batch_id=None, scenario=None):
    """Extract one table as described by definitions/landing/sql-loads/<table>.yml."""
    batch_id = batch_id or audit.new_batch_id()
    started = dt.datetime.utcnow()
    ex, tgt = spec["extract"], spec["target"]
    key = "%s.%s" % (spec["source_system"], spec["source_object"])
    store = spec["watermark"]["store"]
    wm_col = ex["watermark_column"]
    cols = ", ".join(ex["columns"])
    url = _jdbc_url(spark, env)
    opts = {"url": url, "user": spark_utils.secret(spark, env, "sql_user"), "password": spark_utils.secret(spark, env, "sql_password"),
            "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver", "fetchsize": str(ex.get("fetch_size", 5000))}

    def read(query, partition=None):
        r = spark.read.format("jdbc").options(**opts).option("dbtable", "(%s) src" % query)
        if partition:
            r = r.options(**partition)
        return r.load()

    # 1. upper bound for this run (so rows changing mid-run are picked up next time, never lost)
    hi = read("SELECT MAX(%s) AS hi FROM %s" % (wm_col, spec["source_object"])).collect()[0][0]
    if hi is None:
        audit.log_run(spark, spec["audit"]["run_log"], batch_id=batch_id, layer="landing", source_system=spec["source_system"],
                      table_name=spec["table"], scenario=scenario, status="NO_DATA", rows_processed=0, started_ts=started,
                      finished_ts=dt.datetime.utcnow(), details="source table empty")
        return 0
    lo = watermarks.get_watermark(spark, store, key) if ex["load_type"] == "incremental" else None
    where = "%s <= '%s'" % (wm_col, hi) + ("" if lo is None else " AND %s > '%s'" % (wm_col, lo))
    query = "SELECT %s FROM %s WHERE %s" % (cols, spec["source_object"], where)

    # 2. optional parallel read
    part = None
    if ex.get("num_partitions", 1) > 1 and ex.get("partition_column"):
        pc = ex["partition_column"]
        b = read("SELECT MIN(%s) AS a, MAX(%s) AS b FROM (%s) q" % (pc, pc, query)).collect()[0]
        if b[0] is not None and b[0] != b[1]:
            part = {"partitionColumn": pc, "lowerBound": str(b[0]), "upperBound": str(b[1]), "numPartitions": str(ex["num_partitions"])}

    df = read(query, part)
    out = config.storage_uri(env, tgt["container"], "%s/ingest_date=%s/batch_id=%s" % (tgt["path"], dt.date.today().isoformat(), batch_id))
    df.write.mode("append").format(tgt["format"]).save(out)
    n = spark.read.format(tgt["format"]).load(out).count()

    # 3. advance the watermark only after the files are safely written
    if spec["watermark"].get("advance_after_success", True):
        watermarks.set_watermark(spark, store, key, hi, batch_id)
    audit.log_run(spark, spec["audit"]["run_log"], batch_id=batch_id, layer="landing", source_system=spec["source_system"],
                  table_name=spec["table"], scenario=scenario, status="SUCCESS", rows_processed=n, started_ts=started,
                  finished_ts=dt.datetime.utcnow(), details="range (%s, %s] -> %s" % (lo, hi, out))
    return n
