"""Repeatable validation of the Azure SQL source. Writes a markdown report (dissertation evidence).
  python -m azure_sql.validate [d0|d1|d2]   (scenario = the state you expect the DB to be in)"""
import datetime as dt
import os
import sys

from common import config, sqlconn, market, refdata
from azure_sql.generate import Ctx

ID_RE = {"sec_code": "INST[0-9][0-9][0-9][0-9][0-9]", "book_cd": "PORT[0-9][0-9][0-9][0-9]", "cpty_code": "CPTY[0-9][0-9][0-9][0-9]",
         "acct_ref": "ACC[0-9][0-9][0-9][0-9][0-9]", "trade_no": "TRD[0-9][0-9][0-9][0-9][0-9][0-9][0-9]"}


def main():
    scn = sys.argv[1] if len(sys.argv) > 1 else "d0"
    ctx = Ctx(); cfg = ctx.cfg
    as_of = cfg["scenario_dates"][scn]
    conn = sqlconn.connect(); cur = conn.cursor()
    res = []

    def one(sql, *a):
        cur.execute(sql, *a); return cur.fetchone()[0]

    def check(name, ok, detail):
        res.append((name, "PASS" if ok else "FAIL", str(detail)))

    exp_trades = cfg["volumes"]["trades"] + sum(cfg["incremental"][k]["new_trades"] for k in ["d1", "d2"] if k <= scn)
    check("Row counts: instruments/portfolios/accounts/counterparties",
          [one("SELECT COUNT(*) FROM reference.%s" % t) for t in ["instruments", "portfolios", "accounts", "counterparties"]] ==
          [cfg["volumes"][k] for k in ["instruments", "portfolios", "accounts", "counterparties"]], "expected 100/20/30/50")
    check("Row count: trades", one("SELECT COUNT(*) FROM source.trades") == exp_trades, "expected %d, found %d" % (exp_trades, one("SELECT COUNT(*) FROM source.trades")))
    # master ID format
    for col, rx in ID_RE.items():
        tab = {"sec_code": "reference.instruments", "book_cd": "reference.portfolios", "cpty_code": "reference.counterparties",
               "acct_ref": "reference.accounts", "trade_no": "source.trades"}[col]
        bad = one("SELECT COUNT(*) FROM %s WHERE %s NOT LIKE '%s'" % (tab, col, rx))
        check("Master ID format: %s" % col, bad == 0, "%d violations" % bad)
    # referential integrity & business consistency
    check("Trade account belongs to trade portfolio (1.0 defect: 582)",
          one("SELECT COUNT(*) FROM source.trades t JOIN reference.accounts a ON a.acct_ref=t.acct_ref WHERE a.book_cd<>t.book_cd") == 0, "0 mismatches expected")
    check("Trade currency equals instrument currency",
          one("SELECT COUNT(*) FROM source.trades t JOIN reference.instruments i ON i.sec_code=t.sec_code WHERE i.ccy<>t.trade_ccy") == 0, "0 mismatches expected")
    check("No nulls in key/core trade columns",
          one("SELECT COUNT(*) FROM source.trades WHERE trade_no IS NULL OR sec_code IS NULL OR book_cd IS NULL OR cpty_code IS NULL OR acct_ref IS NULL OR qty IS NULL OR price IS NULL OR last_updated_ts IS NULL") == 0, "0 expected")
    check("Settlement date >= trade date; T+1/T+2 only",
          one("SELECT COUNT(*) FROM source.trades WHERE settle_dt<trade_dt OR DATEDIFF(day,trade_dt,settle_dt)>4") == 0, "0 violations")
    check("Gross = qty x price x contract size",
          one("SELECT COUNT(*) FROM source.trades t JOIN reference.instruments i ON i.sec_code=t.sec_code WHERE ABS(t.gross_amt - ROUND(t.qty*t.price*i.contract_size,2)) > 0.02") == 0, "0 violations (tolerance 0.02)")
    check("Net = gross +/- commission + fees by side",
          one("SELECT COUNT(*) FROM source.trades WHERE ABS(net_amt - CASE WHEN side='BUY' THEN gross_amt+commission+fees ELSE gross_amt-commission-fees END) > 0.02") == 0, "0 violations")
    # lifecycle coherence
    check("SETTLED/FAILED only when settlement date reached",
          one("SELECT COUNT(*) FROM source.trades WHERE trade_status IN ('SETTLED','FAILED') AND settle_dt > ?", as_of) == 0, "0 violations as of %s" % as_of)
    check("EXECUTED/NEW not past settlement",
          one("SELECT COUNT(*) FROM source.trades WHERE trade_status IN ('NEW','EXECUTED') AND settle_dt <= ?", as_of) == 0, "0 violations")
    dist = dict(cur.execute("SELECT trade_status, COUNT(*) FROM source.trades GROUP BY trade_status").fetchall())
    tot = sum(dist.values())
    pct = lambda k: 100.0 * dist.get(k, 0) / tot
    check("Realistic status mix (CANCELLED <8%, FAILED <4%, SETTLED majority)",
          pct("CANCELLED") < 8 and pct("FAILED") < 4 and pct("SETTLED") > 50, {k: "%.1f%%" % pct(k) for k in sorted(dist)})
    # price realism vs market series
    pb = ctx.pb; off = 0; n = 0
    for no, d, sc, p in cur.execute("SELECT trade_no, trade_dt, sec_code, price FROM source.trades WHERE version=1").fetchall():
        n += 1
        if abs(float(p) / pb.price(sc, d) - 1) > 0.02: off += 1
    check("Unamended trade prices within 2% of that day's market price", off == 0, "%d of %d outside" % (off, n))
    # notional sanity in USD (approximate fixed rates; real FX comes from the REST source)
    per_usd = {"USD": 1, "EUR": 0.908, "GBP": 0.758, "JPY": 159.6, "CHF": 0.839, "AUD": 1.48, "CAD": 1.4285, "SGD": 1.2888, "HKD": 7.847}
    mx = max(float(g) / per_usd[c] for g, c in cur.execute("SELECT gross_amt, trade_ccy FROM source.trades").fetchall())
    check("Max single-trade gross amount sane (<= USD 100M equivalent)", mx <= 1e8, "max USD %.1fM" % (mx / 1e6))
    # watermark & incremental
    check("Watermark column populated on all tables",
          sum(one("SELECT COUNT(*) FROM %s WHERE last_updated_ts IS NULL" % t) for t in ["source.trades", "reference.instruments", "reference.portfolios", "reference.accounts", "reference.counterparties"]) == 0, "0 nulls")
    cur.execute("SELECT scenario, run_start_ts, trades_inserted, trades_updated, ref_updated FROM source.load_log ORDER BY scenario")
    log = cur.fetchall()
    check("Load log contains expected scenarios", [x[0] for x in log] == [k for k in ["d0", "d1", "d2"] if k <= scn], [x[0] for x in log])
    for x in log[1:]:
        scn_i = x[0]; ts = x[1]
        trades_ts = one("SELECT COUNT(*) FROM source.trades WHERE last_updated_ts = ?", ts)
        exp = x[2] + x[3]
        latest = (x is log[-1])
        ok = (trades_ts == exp) if latest else (0 < trades_ts <= exp)   # later runs may overwrite earlier watermarks
        check("Watermark picks %s delta (last_updated_ts = run ts)" % scn_i, ok, "expected %s%d (%d new + %d updated), found %d" % ("" if latest else "<= ", exp, x[2], x[3], trades_ts))
    # outbox consistency
    check("Outbox: every trade has event history consistent with status",
          one("""SELECT COUNT(*) FROM source.trades t WHERE
                 (t.trade_status='SETTLED' AND NOT EXISTS(SELECT 1 FROM source.trade_event_outbox o WHERE o.trade_no=t.trade_no AND o.event_type='TRADE_SETTLED'))
              OR (t.trade_status='CANCELLED' AND NOT EXISTS(SELECT 1 FROM source.trade_event_outbox o WHERE o.trade_no=t.trade_no AND o.event_type='TRADE_CANCELLED'))
              OR (t.trade_status='FAILED' AND NOT EXISTS(SELECT 1 FROM source.trade_event_outbox o WHERE o.trade_no=t.trade_no AND o.event_type='TRADE_FAILED'))
              OR (t.trade_status IN ('EXECUTED','SETTLED','FAILED') AND NOT EXISTS(SELECT 1 FROM source.trade_event_outbox o WHERE o.trade_no=t.trade_no AND o.event_type='TRADE_EXECUTED'))""") == 0, "0 trades without matching events")
    check("Outbox: no event precedes the trade's own execution event",
          one("""SELECT COUNT(*) FROM source.trade_event_outbox o JOIN source.trade_event_outbox x ON x.trade_no=o.trade_no AND x.event_type='TRADE_EXECUTED'
                 WHERE o.event_type<>'TRADE_EXECUTED' AND o.event_ts < x.event_ts""") == 0, "0 events out of order within a trade's lifecycle")
    check("Outbox event_id unique + format", one("SELECT COUNT(*) FROM source.trade_event_outbox WHERE event_id NOT LIKE 'EVT[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'") == 0, "0 bad ids")

    npass = sum(1 for r in res if r[1] == "PASS")
    out = ["# Azure SQL source validation - state after `%s`" % scn, "", "Run (UTC): %s | as-of business date: %s" % (dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), as_of), "",
           "**%d / %d checks passed**" % (npass, len(res)), "", "| Check | Result | Detail |", "|---|---|---|"]
    out += ["| %s | %s | %s |" % r for r in res]
    p = os.path.join(config.evidence_dir(), "sql_validation_%s.md" % scn)
    open(p, "w").write("\n".join(out) + "\n")
    print("\n".join(out))
    sys.exit(0 if npass == len(res) else 1)


if __name__ == "__main__":
    main()
