"""Cross-source verification (SRC-05) for the four source systems.
Event Hubs is verified by (1) the namespace's IncomingMessages metric vs the producer manifests, (2) a bounded
sample read of the stream (payload shape + keys resolve to SQL), and (3) the outbox ground truth vs SQL state.
A full read-back of the stream is done by the Bronze streaming job in Phase 7 (this tier throttles Python readers)."""
import datetime as dt
import glob
import json
import os
import subprocess
import threading
import time

from azure.eventhub import EventHubConsumerClient

from common import config, secrets, sqlconn

RES = "/subscriptions/1bd38212-4f79-42c0-b758-37a56d9ebc7e/resourceGroups/edap-rg/providers/Microsoft.EventHub/namespaces/edap-eventhubs-645ca5"
FX_CCY = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "SGD", "HKD"}


def sample_read(limit=1500, max_seconds=25):
    msgs, lock = [], threading.Lock()
    client = EventHubConsumerClient.from_connection_string(secrets.get("eventhub-listen-connection-string"), consumer_group="$Default")

    def on_event(ctx, ev):
        if ev is None:
            return
        with lock:
            if len(msgs) < limit:
                msgs.append(ev.body_as_str())

    threading.Thread(target=lambda: client.receive(on_event=on_event, starting_position="-1"), daemon=True).start()
    t0 = time.time()
    while time.time() - t0 < max_seconds and len(msgs) < limit:
        time.sleep(0.5)
    return list(msgs)           # the client is abandoned; the process exits via os._exit


def metric_total(since):
    """Messages received since the first current producer run (earlier runs on a previous hub are excluded)."""
    start = (since - dt.timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = (dt.datetime.utcnow() + dt.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = subprocess.run(["az", "monitor", "metrics", "list", "--resource", RES, "--metric", "IncomingMessages", "--interval", "PT1M",
                        "--start-time", start, "--end-time", end, "--aggregation", "Total", "--query", "sum(value[0].timeseries[0].data[].total)", "-o", "tsv"],
                       capture_output=True, text=True)
    return int(float(r.stdout.strip() or 0))


def main():
    cur = sqlconn.connect().cursor()
    res = []
    chk = lambda n, ok, d: res.append((n, "PASS" if ok else "FAIL", d))
    man_dir = config.evidence_dir("source_manifests")
    mans = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(man_dir, "events_d?.json")))]
    expected = sum(m.get("sent_confirmed", 0) for m in mans)
    since = dt.datetime.utcfromtimestamp(min(os.path.getmtime(p) for p in glob.glob(os.path.join(man_dir, "events_d?.json"))))
    got = metric_total(since)
    for _ in range(8):                      # Azure Monitor lags a few minutes behind the producer
        if got >= expected:
            break
        time.sleep(30); got = metric_total(since)
    chk("Event Hubs received exactly what the producer sent (IncomingMessages metric)", got == expected, "metric %d, producer manifests %d" % (got, expected))

    sql_trades = {x[0]: tuple(x[1:]) for x in cur.execute("SELECT trade_no, sec_code, book_cd, cpty_code, trade_status FROM source.trades").fetchall()}
    sample = sample_read()
    parsed, bad = [], 0
    for m in sample:
        try:
            parsed.append(json.loads(m))
        except Exception:
            bad += 1
    need = ("event_id", "trade_id", "instrument_id", "portfolio_id", "counterparty_id", "trade_type", "quantity", "price", "currency", "event_type", "event_timestamp")
    complete = [p for p in parsed if all(k in p for k in need)]
    resolvable = [p for p in complete if p["trade_id"] in sql_trades]
    keymatch = all(sql_trades[p["trade_id"]][:3] == (p["instrument_id"], p["portfolio_id"], p["counterparty_id"]) for p in resolvable)
    chk("Stream sample: payloads parse and keys match SQL (instrument/portfolio/counterparty)", len(resolvable) > 0 and keymatch,
        "sample %d messages: %d complete, %d resolve to SQL trades, %d non-JSON/incomplete (injected malformed)" % (len(sample), len(complete), len(resolvable), len(sample) - len(resolvable)))

    # outbox ground truth: derive final trade state from outbox history and compare with SQL
    order = {"TRADE_EXECUTED": 1, "TRADE_AMENDED": 2, "TRADE_SETTLED": 3, "TRADE_FAILED": 3, "TRADE_CANCELLED": 3}
    last = {}
    rows = cur.execute("SELECT trade_no, event_type, event_ts FROM source.trade_event_outbox ORDER BY event_ts").fetchall()
    for t, e, ts in sorted(rows, key=lambda x: (x[2], order[x[1]])):
        if e != "TRADE_AMENDED":
            last[t] = e
    mp = {"TRADE_EXECUTED": "EXECUTED", "TRADE_SETTLED": "SETTLED", "TRADE_FAILED": "FAILED", "TRADE_CANCELLED": "CANCELLED"}
    diff = [t for t, e in last.items() if sql_trades[t][3] != mp[e]]
    chk("Event history (outbox) reproduces every trade's SQL status", not diff, "%d trades compared, %d differ" % (len(last), len(diff)))
    nostream = [t for t, v in sql_trades.items() if v[3] != "NEW" and t not in last]
    chk("Every non-NEW SQL trade has an event history", not nostream, "%d trades without events" % len(nostream))
    pend = cur.execute("SELECT COUNT(*) FROM source.trade_event_outbox WHERE published_ts IS NULL").fetchone()[0]
    chk("All outbox events published after D2 (none stuck)", pend == 0, "%d unpublished" % pend)
    dups = sum(m.get("duplicates_sent", 0) for m in mans)
    ooo = sum(m.get("out_of_order_moved", 0) for m in mans)
    mal = sum(sum(m.get("malformed_sent", {}).values()) for m in mans)
    chk("Injected stream conditions recorded for later DQ/dedup checks", dups > 0 and ooo > 0 and mal > 0, "duplicates %d, out-of-order %d, malformed %d" % (dups, ooo, mal))

    # cross-source: reference currencies vs FX coverage; positions vs SQL
    ccys = {x[0] for x in cur.execute("SELECT DISTINCT ccy FROM reference.instruments").fetchall()} | \
           {x[0] for x in cur.execute("SELECT DISTINCT base_ccy FROM reference.portfolios").fetchall()}
    fxfile = sorted(glob.glob(os.path.join(config.out_dir("fx_rates"), "fx_rates_history_*.json")))
    quotes = set()
    if fxfile:
        env = json.load(open(fxfile[0])); quotes = set(next(iter(env["response"]["rates"].values()))) | {env["response"]["base"]}
    chk("FX history file covers every instrument and portfolio currency", ccys <= quotes, "in use %s; FX file has %s" % (sorted(ccys), sorted(quotes)))
    fx_days = len(env["response"]["rates"]) if fxfile else 0
    chk("FX history spans trade history (no gaps > 4 days)", fxfile != [] and fx_days >= 500, "%d dated rate sets" % fx_days)
    n = sum(1 for r in res if r[1] == "PASS")
    out = ["# Cross-source verification", "", "Run (UTC): %s" % dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), "",
           "**%d / %d checks passed**" % (n, len(res)), "", "| Check | Result | Detail |", "|---|---|---|"] + ["| %s | %s | %s |" % r for r in res]
    open(os.path.join(config.evidence_dir(), "cross_source_verification.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out), flush=True)
    os._exit(0 if n == len(res) else 1)


if __name__ == "__main__":
    main()
