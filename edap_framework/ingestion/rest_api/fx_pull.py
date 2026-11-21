"""Landing for the FX REST API, as small functions: fetch_fx -> write_fx -> register_fx."""
import datetime as dt
import json
import time

import requests

from edap_framework.core import config, spark_utils
from edap_framework.ingestion.files.arrival import REG_DDL, REG_SCHEMA


def _get(spec, path):
    api = spec["api"]
    params = {"base": api["base_currency"], "symbols": ",".join(api["symbols"])}
    last = None
    for attempt in range(1, api["retry"]["attempts"] + 1):
        try:
            r = requests.get("%s/%s" % (api["base_url"], path), params=params, timeout=api["timeout_seconds"])
            if r.status_code == 200:
                return r.url, r.status_code, r.json()
            last = "HTTP %s" % r.status_code
        except requests.RequestException as e:
            last = str(e)
        time.sleep(api["retry"]["backoff_seconds"] * attempt)
    raise RuntimeError("FX API failed after %d attempts: %s" % (api["retry"]["attempts"], last))


def fetch_fx(spec, mode, business_date):
    """mode = history | daily. Returns the envelope plus the file name it will be stored under."""
    m = spec["modes"][mode]
    if mode == "history":
        start, end = m["start_date"], business_date
        url, code, body = _get(spec, "%s..%s" % (start, end))
        fname, requested, stale = m["file"].format(start=start.replace("-", ""), end=end.replace("-", "")), end, False
    else:
        url, code, body = _get(spec, business_date)
        requested, stale = business_date, body.get("date") != business_date          # stale_rule
        fname = m["file"].format(date=business_date.replace("-", ""))
        if stale:
            fname = fname.replace(".json", "_stale.json")
    env_ = {"request": url, "requested_date": requested, "fetched_at_utc": dt.datetime.utcnow().isoformat() + "Z",
            "http_status": code, "stale": stale, "response": body}
    return {"file_name": fname, "envelope": env_, "stale": stale, "requested_date": requested}


def write_fx(spark, spec, env, result):
    t = spec["target"]
    path = config.storage_uri(env, t["container"], "%s/%s" % (t["path"], result["file_name"]))
    spark_utils.get_dbutils(spark).fs.put(path, json.dumps(result["envelope"]), True)
    return path


def register_fx(spark, spec, result, path, batch_id):
    reg = spec["registry"]["table"]
    spark.sql(REG_DDL.format(t=reg))
    now = dt.datetime.utcnow()
    spark.createDataFrame([(result["file_name"], path, len(json.dumps(result["envelope"])), result["requested_date"].replace("-", ""), 1, now, now,
                            batch_id, "STALE" if result["stale"] else "REGISTERED")], REG_SCHEMA).write.mode("append").saveAsTable(reg)
    return 1
