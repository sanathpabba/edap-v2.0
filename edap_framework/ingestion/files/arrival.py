"""Landing for file sources: source drop -> checks -> landing (content never altered) -> registry.

scan_source_drop -> check_expected_file / check_file (whole-file checks) -> copy_to_landing | quarantine_file -> register_arrivals
A failed whole-file check means the file is wrong as a whole: it is copied to landing/<x>/quarantine (not to inbound) and the pipeline halts."""
import datetime as dt
import re

from edap_framework.core import config, spark_utils

REG_DDL = """CREATE TABLE IF NOT EXISTS {t} (
  file_name STRING, file_path STRING, size_bytes BIGINT, business_date STRING, version INT,
  arrived_ts TIMESTAMP, registered_ts TIMESTAMP, batch_id STRING, status STRING)"""
REG_SCHEMA = ("file_name string, file_path string, size_bytes long, business_date string, version int, "
              "arrived_ts timestamp, registered_ts timestamp, batch_id string, status string")


# ---------- pure helpers (unit-tested)
def previous_business_day(day):
    d = day - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def header_problems(header_line, expected, delimiter=","):
    cols = [c.strip().strip('"') for c in header_line.strip().split(delimiter)]
    missing, extra = [c for c in expected if c not in cols], [c for c in cols if c not in expected]
    problems = []
    if missing:
        problems.append("header is missing column(s): %s" % ", ".join(missing))
    if extra:
        problems.append("header has unexpected column(s): %s" % ", ".join(extra))
    if not missing and not extra and cols != list(expected):
        problems.append("header columns are in a different order than expected")
    return problems


def parse_name(spec, name):
    arr = spec["arrival"]
    m = re.compile(arr["file_pattern"]).match(name)
    if not m:
        return None, None
    return m.group(arr["business_date_group"]), int(m.group(arr["version_group"]) or 1)


# ---------- spark/dbutils steps
def _registry_known(spark, spec, rescan):
    reg = spec["registry"]["table"]
    spark.sql(REG_DDL.format(t=reg))
    return set() if rescan else {(r[0], r[1]) for r in spark.sql("SELECT file_name, size_bytes FROM %s" % reg).collect()}


def scan_source_drop(spark, spec, env, rescan=False):
    """Every file in the source drop, flagged new (not yet registered with the same name+size) or known."""
    sd = spec["source_drop"]
    known = _registry_known(spark, spec, rescan)
    out = []
    for f in spark_utils.get_dbutils(spark).fs.ls(config.storage_uri(env, sd["container"], sd["path"])):
        if f.isDir():
            continue
        bdate, ver = parse_name(spec, f.name)
        out.append({"name": f.name, "path": f.path, "size": f.size, "modified": dt.datetime.utcfromtimestamp(f.modificationTime / 1000.0),
                    "business_date": bdate, "version": ver, "new": (f.name, f.size) not in known})
    return out


def check_expected_file(spec, all_files, today):
    """'File not received': the file for the expected business date is missing from the source drop. Returns a problem text or None."""
    exp = (spec.get("file_checks") or {}).get("expected_file")
    if not exp:
        return None
    d = previous_business_day(today) if exp["business_date"] == "previous_business_day" else today
    want = d.strftime("%Y%m%d")
    if any(f["business_date"] == want for f in all_files):
        return None
    return "expected file %s (business date %s) was not received in the source drop" % (exp["pattern"].format(date=want), d.isoformat())


def check_file(spark, spec, env, f):
    """Whole-file checks: recognised name, readable, right header, not empty. Returns a list of problems (empty = file is fine)."""
    fc, problems = spec.get("file_checks") or {}, []
    if f["business_date"] is None:
        problems.append("file name does not match the expected pattern %s" % spec["arrival"]["file_pattern"])
    try:
        head = spark_utils.get_dbutils(spark).fs.head(f["path"], 8192)
        first = head.splitlines()[0] if head.splitlines() else ""
    except Exception as exc:                                                    # noqa: BLE001
        return problems + ["file cannot be read (%s)" % str(exc)[:120]]
    if fc.get("header") and not first:
        problems.append("file is empty (no header line)")
    elif fc.get("header"):
        problems += header_problems(first, fc["header"], config.load_yaml(spec["source_definition"]).get("delimiter", ","))
    if not problems and fc.get("min_data_rows") is not None:
        rows = spark.read.text(f["path"]).count() - (1 if fc.get("header") else 0)
        if rows < fc["min_data_rows"]:
            problems.append("file has %d data row(s); at least %d expected" % (rows, fc["min_data_rows"]))
    return problems


def copy_to_landing(spark, spec, env, f):
    a = spec["arrival"]
    dest = config.storage_uri(env, a["container"], "%s/%s" % (a["inbound_path"], f["name"]))
    spark_utils.get_dbutils(spark).fs.cp(f["path"], dest, True)
    if spec["source_drop"].get("after_copy") == "move_to_processed":
        sd = spec["source_drop"]
        spark_utils.get_dbutils(spark).fs.mv(f["path"], config.storage_uri(env, sd["container"], "%s/processed/%s" % (sd["path"], f["name"])))
    return dest


def quarantine_file(spark, spec, env, f):
    a = spec["arrival"]
    dest = config.storage_uri(env, a["container"], "%s/%s" % (a["quarantine_path"], f["name"]))
    spark_utils.get_dbutils(spark).fs.cp(f["path"], dest, True)
    return dest


def registry_row(f, landing_path, batch_id, status):
    return (f["name"], landing_path, f["size"], f["business_date"], f["version"], f["modified"], dt.datetime.utcnow(), batch_id, status)


def register_arrivals(spark, spec, rows):
    if rows:
        spark.createDataFrame(rows, REG_SCHEMA).write.mode("append").saveAsTable(spec["registry"]["table"])
    return len(rows)
