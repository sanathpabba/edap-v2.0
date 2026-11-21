"""FX rates REST source (real public API, no credentials): frankfurter.dev (ECB reference rates).
  python -m fx_rates.fetch d0      -> full history up to D0 (one range call)
  python -m fx_rates.fetch d1|d2   -> daily pull for that business date
  python -m fx_rates.fetch stale   -> weekend date: API returns the previous business day => flagged stale
Raw API responses are preserved in an envelope {request, fetched_at_utc, http_status, stale, response}."""
import datetime as dt
import json
import os
import sys
import time

import requests

from common import config

NEEDED = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "SGD", "HKD"]


class FxClient:
    def __init__(self, cfg, retries=3, backoff=2.0):
        self.base, self.base_ccy = cfg["fx"]["api_base"], cfg["fx"]["base_currency"]
        self.symbols = ",".join(c for c in NEEDED if c != self.base_ccy)
        self.retries, self.backoff = retries, backoff

    def get(self, path):
        url = "%s/%s?base=%s&symbols=%s" % (self.base, path, self.base_ccy, self.symbols)
        last = None
        for n in range(1, self.retries + 1):
            try:
                resp = requests.get(url, timeout=20)
                if resp.status_code == 200:
                    body = resp.json()
                    self._validate(body)
                    return url, resp.status_code, body
                last = "HTTP %s" % resp.status_code
            except (requests.RequestException, ValueError) as e:
                last = str(e)[:120]
            time.sleep(self.backoff * n)
        raise RuntimeError("FX API failed after %d attempts: %s" % (self.retries, last))

    def _validate(self, body):
        if "rates" not in body or "base" not in body:
            raise ValueError("unexpected payload shape")
        sample = next(iter(body["rates"].values())) if "start_date" in body else body["rates"]
        missing = [c for c in NEEDED if c != self.base_ccy and c not in sample]
        if missing:
            raise ValueError("missing currencies: %s" % missing)


def save(name, url, status, body, requested, stale):
    env = {"request": url, "requested_date": requested, "fetched_at_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
           "http_status": status, "stale": stale, "response": body}
    p = os.path.join(config.out_dir("fx_rates"), name)
    json.dump(env, open(p, "w"), indent=1)
    return p


def main():
    scn = sys.argv[1]; cfg = config.load(); c = FxClient(cfg); sd = cfg["scenario_dates"]
    if scn == "d0":
        start, end = cfg["history_start"], sd["d0"]
        url, st, body = c.get("%s..%s" % (start, end))
        name = "fx_rates_history_%s_%s.json" % (start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
        save(name, url, st, body, "%s..%s" % (start, end), False)
        info = {"file": name, "days": len(body["rates"]), "first": min(body["rates"]), "last": max(body["rates"])}
    else:
        d = sd[scn] if scn in sd else dt.date(2026, 11, 21)           # 'stale' demo: Saturday after D2
        url, st, body = c.get(str(d))
        stale = body["date"] != str(d)
        name = "fx_rates_%s%s.json" % (d.strftime("%Y%m%d"), "_stale" if stale else "")
        save(name, url, st, body, str(d), stale)
        info = {"file": name, "requested": str(d), "returned_date": body["date"], "stale": stale, "rates": body["rates"]}
    p = os.path.join(config.evidence_dir("source_manifests"), "fx_%s.json" % scn)
    json.dump(info, open(p, "w"), indent=2); print(json.dumps(info, indent=2)[:900])


if __name__ == "__main__":
    main()
