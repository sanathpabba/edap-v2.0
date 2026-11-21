"""Platform reset: return the Databricks side of EDAP to an empty state so a demo (D0, D1, D2) can start from scratch.

DROPS    every table/view/materialized view in the schemas bronze, silver, gold, consumption, quarantine;
         edap.monitoring.{dq_results, dq_summary, notifications}; edap.audit.{ingestion_runs, file_arrivals}; edap.metadata.watermarks
DELETES  landing/{sql, events, fx_rates, positions, _checkpoints} and bronze/_checkpoints (landing files and streaming checkpoints)
KEEPS    reference tables, the governance schema, the artifacts volume, the schemas themselves, the source system's own storage (sourcedrop),
         and everything outside the edap catalog (1.0's catalogs are never touched).
Requires confirm=True; dry_run=True only lists what would happen."""
from edap_framework.core import config

PURGE_SCHEMAS = ["bronze", "silver", "gold", "consumption", "quarantine"]
PURGE_TABLES = {"monitoring": ["dq_results", "dq_summary", "notifications"], "audit": ["ingestion_runs", "file_arrivals"], "metadata": ["watermarks"]}
DELETE_PATHS = [("landing", "sql"), ("landing", "events"), ("landing", "fx_rates"), ("landing", "positions"), ("landing", "_checkpoints"), ("bronze", "_checkpoints")]


def _drop_statement(table_type, fq):
    t = (table_type or "").upper()
    if "MATERIALIZED" in t:
        return "DROP MATERIALIZED VIEW IF EXISTS %s" % fq
    if "VIEW" in t:
        return "DROP VIEW IF EXISTS %s" % fq
    return "DROP TABLE IF EXISTS %s" % fq


def plan(spark, env):
    """What a reset would do: [(statement, fq)] to drop and [uri] to delete. Reads the catalog's information_schema; changes nothing."""
    cat = env["catalog"]
    if cat != "edap":
        raise ValueError("refusing to reset catalog %r: only the 'edap' catalog may be reset" % cat)
    wanted = {s: None for s in PURGE_SCHEMAS}
    wanted.update(PURGE_TABLES)
    drops = []
    rows = spark.sql("SELECT table_schema, table_name, table_type FROM %s.information_schema.tables WHERE table_schema IN (%s)"
                     % (cat, ",".join("'%s'" % s for s in wanted))).collect()
    for r in rows:
        keep_only = wanted[r["table_schema"]]
        if keep_only is not None and r["table_name"] not in keep_only:
            continue                                                         # e.g. nothing else in monitoring/audit/metadata is touched
        fq = "%s.%s.%s" % (cat, r["table_schema"], r["table_name"])
        drops.append((_drop_statement(r["table_type"], fq), fq))
    deletes = [config.storage_uri(env, container, path) for container, path in DELETE_PATHS]
    return {"drop": drops, "delete": deletes}


def reset_platform(spark, dbutils, env, confirm=False, dry_run=False, log=print):
    p = plan(spark, env)
    log("will drop %d object(s) and delete %d folder(s)" % (len(p["drop"]), len(p["delete"])))
    for _, fq in p["drop"]:
        log("  drop   %s" % fq)
    for uri in p["delete"]:
        log("  delete %s" % uri)
    if dry_run:
        log("dry run: nothing changed")
        return {**p, "executed": False}
    if not confirm:
        raise PermissionError("reset is destructive: pass confirm=True (--yes) to run it")
    done = {"dropped": 0, "deleted": 0, "failed": []}
    for statement, fq in p["drop"]:
        try:
            spark.sql(statement)
            done["dropped"] += 1
        except Exception as exc:                                              # noqa: BLE001  keep going, report at the end
            done["failed"].append("%s: %s" % (fq, str(exc)[:160]))
    for uri in p["delete"]:
        try:
            dbutils.fs.rm(uri, True)
            done["deleted"] += 1
        except Exception as exc:                                              # noqa: BLE001
            if "not exist" in str(exc) or "PathNotFound" in str(exc) or "FileNotFound" in str(exc):
                done["deleted"] += 1                                          # nothing there = already clean
            else:
                done["failed"].append("%s: %s" % (uri, str(exc)[:160]))
    log("done: dropped %(dropped)d, deleted %(deleted)d folder(s), %(n)d failure(s)" % {**done, "n": len(done["failed"])})
    for f in done["failed"]:
        log("  FAILED " + f)
    return {**p, "executed": True, **done}
