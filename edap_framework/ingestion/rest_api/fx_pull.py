"""Landing for the FX REST API: call the API with retry/backoff and store the raw response inside a small envelope."""
import datetime as dt
import json
import time

import requests

from edap_framework.core import audit, config, spark_utils
from edap_framework.ingestion.files.arrival import REG_DDL


def _get(spec, path):
    api = spec["api"]
    url = "%s/%s" % (api["base_url"], path)
    params = {"base": api["base_currency"], "symbols": ",".join(api["symbols"])}
    last = None
    for attempt in range(1, api["retry"]["attempts"] + 1):
        try:
            r = requests.get(url, params=params, timeout=api["timeout_seconds"])
            if r.status_code == 200:
                return r.url, r.status_code, r.json()
            last = "HTTP %s" % r.status_code
        except requests.RequestException as e:
            last = str(e)
        time.sleep(api["retry"]["backoff_seconds"] * attempt)
    raise RuntimeError("FX API failed after %d attempts: %s" % (api["retry"]["attempts"], last))


def land_fx(spark, spec, env, mode, business_date, batch_id=None, scenario=None):
    """mode = history | daily ; business_date = 'YYYY-MM-DD'."""
    batch_id = batch_id or audit.new_batch_id()
    started = dt.datetime.utcnow()
    m = spec["modes"][mode]
    if mode == "history":
        start, end = m["start_date"], business_date
        url, code, body = _get(spec, "%s..%s" % (start, end))
        fname = m["file"].format(start=start.replace("-", ""), end=end.replace("-", ""))
        requested, stale = end, False
    else:
        url, code, body = _get(spec, business_date)
        fname = m["file"].format(date=business_date.replace("-", ""))
        requested, stale = business_date, body.get("date") != business_date      # stale_rule
        if stale:
            fname = fname.replace(".json", "_stale.json")
    envelope = {"request": url, "requested_date": requested, "fetched_at_utc": dt.datetime.utcnow().isoformat() + "Z",
                "http_status": code, "stale": stale, "response": body}
    tgt = spec["target"]
    path = config.storage_uri(env, tgt["container"], "%s/%s" % (tgt["path"], fname))
    spark_utils.get_dbutils(spark).fs.put(path, json.dumps(envelope), True)
    reg = spec["registry"]["table"]                       # same file registry as the file source: path -> landing batch
    spark.sql(REG_DDL.format(t=reg))
    now = dt.datetime.utcnow()
    spark.createDataFrame([(fname, path, len(json.dumps(envelope)), requested.replace("-", ""), 1, now, now, batch_id,
                            "STALE" if stale else "REGISTERED")],
                          "file_name string, file_path string, size_bytes long, business_date string, version int, "
                          "arrived_ts timestamp, registered_ts timestamp, batch_id string, status string").write.mode("append").saveAsTable(reg)
    audit.log_run(spark, spec["audit"]["run_log"], batch_id=batch_id, layer="landing", source_system=spec["source_system"],
                  table_name=spec["table"], scenario=scenario, status="STALE" if stale else "SUCCESS", rows_processed=1,
                  started_ts=started, finished_ts=dt.datetime.utcnow(), details=path)
    return path
