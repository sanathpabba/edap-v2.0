"""Landing for relational sources, as small functions (each is called by one pipeline step):
resolve_window -> read_extract -> write_extract -> commit_watermark."""
import datetime as dt

from edap_framework.core import config, spark_utils
from edap_framework.metadata import watermarks


def _opts(spark, env, fetch):
    server = spark_utils.secret(spark, env, "sql_server")
    db = spark_utils.secret(spark, env, "sql_database")
    return {"url": "jdbc:sqlserver://%s.database.windows.net:1433;database=%s;encrypt=true;loginTimeout=30" % (server.split(".")[0], db),
            "user": spark_utils.secret(spark, env, "sql_user"), "password": spark_utils.secret(spark, env, "sql_password"),
            "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver", "fetchsize": str(fetch)}


def _read(spark, opts, query, partition=None):
    r = spark.read.format("jdbc").options(**opts).option("dbtable", "(%s) src" % query)
    if partition:
        r = r.options(**partition)
    return r.load()


def watermark_key(spec):
    return "%s.%s" % (spec["source_system"], spec["source_object"])


def resolve_window(spark, spec, env, adhoc=False, from_ts=None):
    """(lo, hi]: Routine = stored watermark .. current max; Adhoc = from_ts (or full) .. current max. hi is None for an empty table."""
    ex = spec["extract"]
    hi = _read(spark, _opts(spark, env, ex.get("fetch_size", 5000)),
               "SELECT MAX(%s) AS hi FROM %s" % (ex["watermark_column"], spec["source_object"])).collect()[0][0]
    if adhoc:
        lo = from_ts                                              # None = full re-extract
    else:
        lo = watermarks.get_watermark(spark, spec["watermark"]["store"], watermark_key(spec)) if ex["load_type"] == "incremental" else None
    return lo, hi


def read_extract(spark, spec, env, lo, hi):
    ex = spec["extract"]
    wm = ex["watermark_column"]
    where = "%s <= '%s'" % (wm, hi) + ("" if lo is None else " AND %s > '%s'" % (wm, lo))
    query = "SELECT %s FROM %s WHERE %s" % (", ".join(ex["columns"]), spec["source_object"], where)
    opts, part = _opts(spark, env, ex.get("fetch_size", 5000)), None
    if ex.get("num_partitions", 1) > 1 and ex.get("partition_column"):
        pc = ex["partition_column"]
        b = _read(spark, opts, "SELECT MIN(%s) AS a, MAX(%s) AS b FROM (%s) q" % (pc, pc, query)).collect()[0]
        if b[0] is not None and b[0] != b[1]:
            part = {"partitionColumn": pc, "lowerBound": str(b[0]), "upperBound": str(b[1]), "numPartitions": str(ex["num_partitions"])}
    return _read(spark, opts, query, part)


def write_extract(spark, spec, env, df, batch_id):
    t = spec["target"]
    out = config.storage_uri(env, t["container"], "%s/ingest_date=%s/batch_id=%s" % (t["path"], dt.date.today().isoformat(), batch_id))
    df.write.mode("append").format(t["format"]).save(out)
    return out, spark.read.format(t["format"]).load(out).count()


def commit_watermark(spark, spec, hi, batch_id):
    """Advance only forward, and only after the landing files were written."""
    store, key = spec["watermark"]["store"], watermark_key(spec)
    cur = watermarks.get_watermark(spark, store, key)
    if hi is not None and (cur is None or hi > cur):
        watermarks.set_watermark(spark, store, key, hi, batch_id)
        return True
    return False
