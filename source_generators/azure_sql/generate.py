"""Azure SQL source generator.
  python -m azure_sql.generate d0   -> reset schema, load reference + ~5,000 historical trades (initial load)
  python -m azure_sql.generate d1   -> incremental 1 (new trades, lifecycle moves, cancels, amends, ref updates)
  python -m azure_sql.generate d2   -> incremental 2 (adds late-arriving corrections)
  python -m azure_sql.generate status
Everything is seeded (config/generation.yml); manifests go to docs/dissertation_evidence/source_manifests/."""
import datetime as dt
import json
import math
import os
import random
import re
import sys
import zlib

from common import config, refdata, market, sqlconn
from common.calendar import bdays, add_bdays

HERE = os.path.dirname(os.path.abspath(__file__))
BPS = {"EQUITY": 5, "BOND": 2, "FX": 1, "COMMODITY": 3, "DERIVATIVE": 8}
TRADERS = ["A. Chen", "M. Okafor", "S. Tremblay", "J. Patel", "L. Rossi", "K. Nakamura", "E. Dubois", "R. Singh"]
STRATS = ["Market Making", "Hedging", "Arbitrage", "Directional", "Client Flow", "Inventory Mgmt"]


# ---------- helpers ----------
def quantity(r, typ):
    if typ == "EQUITY":
        return float(min(max(round(r.lognormvariate(math.log(1500), 0.9) / 100) * 100, 100), 50000))
    if typ == "BOND":
        return float(min(max(round(r.lognormvariate(math.log(500000), 0.8) / 10000) * 10000, 10000), 5000000))
    if typ == "FX":
        return float(min(max(round(r.lognormvariate(math.log(2000000), 0.8) / 100000) * 100000, 100000), 20000000))
    if typ == "COMMODITY":
        return float(r.randint(1, 60))
    return float(r.randint(5, 500))


def amounts(ins, side, qty, price):
    gross = round(qty * price * float(ins["contract_size"]), 2)
    comm = round(gross * BPS[ins["sec_type"]] / 10000.0, 2)
    fees = round(0.5 + (zlib.crc32(("%s%s" % (qty, price)).encode()) % 2400) / 100.0, 2)
    net = round(gross + comm + fees if side == "BUY" else gross - comm - fees, 2)
    return gross, comm, fees, net


def is_fail(trade_no, rate):
    return zlib.crc32(("f" + trade_no).encode()) % 1000 < rate * 1000


def at(d, r, h0, h1):
    s = r.randint(h0 * 3600, h1 * 3600 - 1)
    return dt.datetime.combine(d, dt.time()) + dt.timedelta(seconds=s)


def later(r, as_of, h0, h1, t):
    """Event time within [h0,h1) on as_of, but never before the trade's own execution (same-day trades)."""
    lo = dt.datetime.combine(as_of, dt.time(h0))
    if t["trade_dt"] == as_of:
        lo = max(lo, t["trade_ts"] + dt.timedelta(minutes=2))
    hi = max(lo + dt.timedelta(minutes=30), dt.datetime.combine(as_of, dt.time(h1)))
    return lo + dt.timedelta(seconds=r.randint(0, int((hi - lo).total_seconds())))


def settle_date(typ, d):
    return add_bdays(d, 1 if typ in ("COMMODITY", "DERIVATIVE") else 2)


class Ctx:
    def __init__(self):
        self.cfg = config.load()
        self.ref = refdata.build(self.cfg)
        self.ins = {i["sec_code"]: i for i in self.ref["instruments"]}
        self.accts_by_pf = {}
        for a in self.ref["accounts"]:
            self.accts_by_pf.setdefault(a["book_cd"], []).append(a)
        self.pb = market.PriceBook(self.cfg, self.ref["instruments"], self.cfg["scenario_dates"]["d2"])
        self.by_type = {}
        for i in self.ref["instruments"]:
            self.by_type.setdefault(i["sec_type"], []).append(i)
        self.pf_by_cd = {p["book_cd"]: p for p in self.ref["portfolios"]}

    def new_trade(self, r, no, tdate):
        pf = r.choice(self.ref["portfolios"])
        # 70% in-strategy, 30% off-strategy (broader portfolio/instrument coverage -> ~2,000 position combinations)
        typ = r.choice(refdata.BU_TYPES[pf["business_unit"]]) if r.random() < 0.7 else r.choice(sorted(self.by_type))
        ins = r.choice(self.by_type[typ])
        side = "BUY" if r.random() < 0.52 else "SELL"
        price = round(self.pb.price(ins["sec_code"], tdate) * (1 + r.gauss(0, 0.003)), 6)
        qty = quantity(r, typ)
        ts = at(tdate, r, 13, 21)
        return dict(trade_no=no, trade_dt=tdate, trade_ts=ts, settle_dt=settle_date(typ, tdate), sec_code=ins["sec_code"],
                    book_cd=pf["book_cd"], cpty_code=r.choice(self.ref["counterparties"])["cpty_code"],
                    acct_ref=r.choice(self.accts_by_pf[pf["book_cd"]])["acct_ref"], side=side, qty=qty, price=price,
                    trade_ccy=ins["ccy"], version=1, trader=r.choice(TRADERS), strategy=r.choice(STRATS), ins=ins)


def exec_batches(cur, sql_text):
    for batch in re.split(r"^GO\s*$", sql_text, flags=re.M):
        if batch.strip():
            cur.execute(batch)


def next_event_no(cur):
    cur.execute("SELECT ISNULL(MAX(CAST(SUBSTRING(event_id,4,9) AS INT)),0) FROM source.trade_event_outbox")
    return cur.fetchone()[0]


def next_trade_no(cur):
    cur.execute("SELECT ISNULL(MAX(CAST(SUBSTRING(trade_no,4,9) AS INT)),0) FROM source.trades")
    return cur.fetchone()[0]


class Outbox:
    def __init__(self, start, scenario, now):
        self.n, self.rows, self.scenario, self.now = start, [], scenario, now

    def add(self, t, etype, ets, qty, price):
        self.n += 1
        self.rows.append(("EVT%08d" % self.n, t["trade_no"], etype, ets, t["sec_code"], t["book_cd"], t["cpty_code"], t["side"],
                          qty, price, t["trade_ccy"], self.scenario, self.now, None))

    def flush(self, cur):
        self.rows.sort(key=lambda x: x[3])
        cur.fast_executemany = True
        cur.executemany("INSERT INTO source.trade_event_outbox VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", self.rows)
        return len(self.rows)


def trade_row(t, status, upd_ts, created_ts, ctx):
    g, c, f, n = amounts(t["ins"], t["side"], t["qty"], t["price"])
    return (t["trade_no"], t["trade_dt"], t["trade_ts"], t["settle_dt"], t["sec_code"], t["book_cd"], t["cpty_code"], t["acct_ref"],
            t["side"], t["qty"], t["price"], t["trade_ccy"], g, c, f, n, status, t["version"], t["trader"], t["strategy"],
            created_ts, upd_ts)


# ---------- D0 ----------
def d0(ctx, conn):
    cfg, r = ctx.cfg, random.Random(ctx.cfg["seed"] + 1)
    as_of = cfg["scenario_dates"]["d0"]
    now = dt.datetime.utcnow().replace(microsecond=0)
    cur = conn.cursor()
    exec_batches(cur, open(os.path.join(HERE, "ddl", "01_schema_and_tables.sql")).read())
    conn.commit()
    start = now
    ref = ctx.ref
    cur.fast_executemany = True
    old = start - dt.timedelta(days=30)
    cur.executemany("INSERT INTO reference.instruments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [(i["sec_code"], i["sec_name"], i["sec_type"], i["ccy"], i["exchange"], i["ticker"], i["isin"], i["sector"],
                      i["country"], i["contract_size"], i["is_active"], old, old) for i in ref["instruments"]])
    cur.executemany("INSERT INTO reference.portfolios VALUES (?,?,?,?,?,?,?,?)",
                    [(p["book_cd"], p["book_name"], p["business_unit"], p["base_ccy"], p["region"], p["is_active"], old, old) for p in ref["portfolios"]])
    cur.executemany("INSERT INTO reference.counterparties VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [(c["cpty_code"], c["cpty_name"], c["cpty_type"], c["country"], c["risk_category"], c["credit_rating"], c["lei"], c["is_active"], old, old) for c in ref["counterparties"]])
    cur.executemany("INSERT INTO reference.accounts VALUES (?,?,?,?,?,?,?,?,?)",
                    [(a["acct_ref"], a["acct_name"], a["acct_type"], a["ccy"], a["book_cd"], a["custodian"], a["is_active"], old, old) for a in ref["accounts"]])
    n_ref = len(ref["instruments"]) + len(ref["portfolios"]) + len(ref["counterparties"]) + len(ref["accounts"])

    days = bdays(cfg["history_start"], as_of)
    weights = [0.7 + 0.6 * k / (len(days) - 1) for k in range(len(days))]
    tdates = sorted(r.choices(days, weights=weights, k=cfg["volumes"]["trades"]))
    tc = cfg["trades"]
    trades, ob = [], Outbox(0, "d0", start)
    batch = []
    for k, td in enumerate(tdates, 1):
        t = ctx.new_trade(r, "TRD%07d" % k, td)
        typ, ins = t["ins"]["sec_type"], t["ins"]
        pending = (td == as_of and r.random() < tc["d0_pending_rate"])
        exec_ts = t["trade_ts"] + dt.timedelta(seconds=r.randint(1, 45))
        last = t["trade_ts"]
        status = "NEW"
        if not pending:
            ob.add(t, "TRADE_EXECUTED", exec_ts, t["qty"], t["price"])
            last, status = exec_ts, "EXECUTED"
            horizon = min(dt.datetime.combine(t["settle_dt"], dt.time(17)), dt.datetime.combine(as_of, dt.time(17)))
            span = max(int((horizon - exec_ts).total_seconds()), 10)
            if r.random() < tc["cancel_rate"] and horizon > exec_ts:
                cts = exec_ts + dt.timedelta(seconds=r.randint(5, span))
                ob.add(t, "TRADE_CANCELLED", cts, t["qty"], t["price"])
                last, status = cts, "CANCELLED"
            else:
                if r.random() < tc["amend_rate_history"] and horizon > exec_ts:
                    ats = exec_ts + dt.timedelta(seconds=r.randint(5, span))
                    t["qty"] = max(float(round(t["qty"] * r.choice([0.5, 0.8, 1.2, 1.5]) / 100) * 100) if typ == "EQUITY" else round(t["qty"] * r.choice([0.5, 0.8, 1.2, 1.5])), 1.0)
                    t["price"] = round(t["price"] * (1 + r.gauss(0, 0.002)), 6)
                    t["version"] = 2
                    ob.add(t, "TRADE_AMENDED", ats, t["qty"], t["price"])
                    last = ats
                sd = dt.datetime.combine(t["settle_dt"], dt.time(17)) + dt.timedelta(seconds=r.randint(0, 3600))
                if t["settle_dt"] <= as_of:
                    if is_fail(t["trade_no"], tc["fail_rate"]):
                        ob.add(t, "TRADE_FAILED", sd, t["qty"], t["price"])
                        status = "FAILED"
                    else:
                        ob.add(t, "TRADE_SETTLED", sd, t["qty"], t["price"])
                        status = "SETTLED"
                    last = sd
        batch.append(trade_row(t, status, last, t["trade_ts"] + dt.timedelta(seconds=1), ctx))
    cur.fast_executemany = True
    cur.executemany("INSERT INTO source.trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
    n_ob = ob.flush(cur)
    end = dt.datetime.utcnow().replace(microsecond=0)
    cur.execute("INSERT INTO source.load_log VALUES (?,?,?,?,?,?,?,?,?)", "d0", as_of, start, end, len(batch), 0, n_ref, 0, n_ob)
    conn.commit()
    return dict(scenario="d0", as_of=str(as_of), run_start_utc=str(start), trades_inserted=len(batch), ref_rows_inserted=n_ref,
                outbox_rows=n_ob)


# ---------- D1 / D2 ----------
def increment(ctx, conn, scn):
    cfg = ctx.cfg
    inc = cfg["incremental"][scn]
    as_of = cfg["scenario_dates"][scn]
    r = random.Random(cfg["seed"] + {"d1": 11, "d2": 22}[scn])
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM source.load_log WHERE scenario='d0'")
    if not cur.fetchone():
        sys.exit("D0 has not been loaded. Run: d0")
    cur.execute("SELECT 1 FROM source.load_log WHERE scenario=?", scn)
    if cur.fetchone():
        sys.exit("%s already applied. Re-run d0 to reset." % scn)
    run_ts = dt.datetime.utcnow().replace(microsecond=0) + dt.timedelta(seconds=2)
    ob = Outbox(next_event_no(cur), scn, run_ts)
    touched = {"lifecycle": [], "cancel": [], "amend": [], "late": [], "new": []}
    tc = cfg["trades"]

    def load(no):
        cur.execute("SELECT trade_no,trade_dt,trade_ts,settle_dt,sec_code,book_cd,cpty_code,acct_ref,side,qty,price,trade_ccy,version,trader,strategy,trade_status FROM source.trades WHERE trade_no=?", no)
        x = cur.fetchone()
        t = dict(trade_no=x[0], trade_dt=x[1], trade_ts=x[2], settle_dt=x[3], sec_code=x[4], book_cd=x[5], cpty_code=x[6], acct_ref=x[7],
                 side=x[8], qty=float(x[9]), price=float(x[10]), trade_ccy=x[11], version=x[12], trader=x[13], strategy=x[14], ins=ctx.ins[x[4]])
        return t, x[15]

    def write(t, status):
        g, c, f, n = amounts(t["ins"], t["side"], t["qty"], t["price"])
        cur.execute("UPDATE source.trades SET qty=?,price=?,gross_amt=?,commission=?,fees=?,net_amt=?,trade_status=?,version=?,last_updated_ts=? WHERE trade_no=?",
                    t["qty"], t["price"], g, c, f, n, status, t["version"], run_ts, t["trade_no"])

    touched_set = set()
    # 1) lifecycle advancement
    cur.execute("SELECT trade_no, trade_status, settle_dt FROM source.trades WHERE (trade_status='NEW' AND trade_dt<?) OR (trade_status='EXECUTED' AND settle_dt<=?)", as_of, as_of)
    for no, st, sd in cur.fetchall():
        t, _ = load(no)
        final = "EXECUTED"
        if st == "NEW":
            ob.add(t, "TRADE_EXECUTED", at(as_of, r, 9, 11), t["qty"], t["price"])
        if sd <= as_of:
            et = "TRADE_FAILED" if is_fail(no, tc["fail_rate"]) else "TRADE_SETTLED"
            ob.add(t, et, at(as_of, r, 16, 18), t["qty"], t["price"]); final = "FAILED" if et == "TRADE_FAILED" else "SETTLED"
        write(t, final)
        touched_set.add(no); touched["lifecycle"].append(no)

    def pick(statuses, n, extra=""):
        cur.execute("SELECT trade_no FROM source.trades WHERE trade_status IN (%s) %s" % (",".join("'%s'" % s for s in statuses), extra))
        pool = [x[0] for x in cur.fetchall() if x[0] not in touched_set]
        r.shuffle(pool)
        return pool[:n]

    # 2) new trades on this business date (inserted first so cancels/amends can also hit today's executed trades)
    start_no = next_trade_no(cur)
    rows = []
    for k in range(1, inc["new_trades"] + 1):
        t = ctx.new_trade(r, "TRD%07d" % (start_no + k), as_of)
        if r.random() < tc["d0_pending_rate"]:
            status, last = "NEW", t["trade_ts"]
        else:
            ets = t["trade_ts"] + dt.timedelta(seconds=r.randint(1, 45))
            ob.add(t, "TRADE_EXECUTED", ets, t["qty"], t["price"]); status, last = "EXECUTED", ets
        rows.append(trade_row(t, status, run_ts, t["trade_ts"] + dt.timedelta(seconds=1), ctx))
        touched["new"].append(t["trade_no"])
    cur.fast_executemany = True
    cur.executemany("INSERT INTO source.trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    new_set = set(touched["new"])

    # 3) cancels
    for no in pick(["EXECUTED"], inc["cancels"]):
        t, st = load(no)
        ob.add(t, "TRADE_CANCELLED", later(r, as_of, 10, 16, t), t["qty"], t["price"]); write(t, "CANCELLED")
        touched_set.add(no); touched["cancel"].append(no)
    # 4) amends
    for no in pick(["EXECUTED"], inc["amends"]):
        t, st = load(no)
        if r.random() < 0.5:
            t["qty"] = max(round(t["qty"] * r.choice([0.5, 0.8, 1.2, 1.5])), 1.0)
        else:
            t["price"] = round(t["price"] * (1 + r.gauss(0, 0.004)), 6)
        t["version"] += 1
        ob.add(t, "TRADE_AMENDED", later(r, as_of, 10, 16, t), t["qty"], t["price"]); write(t, st)
        touched_set.add(no); touched["amend"].append(no)
    # 5) late-arriving corrections to old settled trades
    cutoff = as_of - dt.timedelta(days=30)
    for no in pick(["SETTLED"], inc["late_updates"], "AND trade_dt < '%s'" % cutoff):
        t, st = load(no)
        t["price"] = round(t["price"] * (1 + r.gauss(0, 0.003)), 6)
        t["version"] += 1
        ob.add(t, "TRADE_AMENDED", at(as_of, r, 9, 17), t["qty"], t["price"]); write(t, st)
        touched_set.add(no); touched["late"].append(no)
    # 6) reference updates (counterparty rating changes)
    ref_changed = []
    ratings = refdata.RATINGS
    cur.execute("SELECT cpty_code, credit_rating FROM reference.counterparties")
    pool = cur.fetchall(); r.shuffle(pool)
    for code, rt in pool[: inc["ref_updates"]]:
        new = ratings[min(max(ratings.index(rt) + r.choice([-1, 1]), 0), len(ratings) - 1)]
        risk = {"AAA": "LOW", "AA": "LOW", "A": "MEDIUM", "BBB": "MEDIUM", "BB": "HIGH"}[new]
        cur.execute("UPDATE reference.counterparties SET credit_rating=?, risk_category=?, last_updated_ts=? WHERE cpty_code=?", new, risk, run_ts, code)
        ref_changed.append("%s:%s->%s" % (code, rt, new))
    n_ob = ob.flush(cur)
    n_upd = len(touched_set - new_set)
    end = dt.datetime.utcnow().replace(microsecond=0)
    cur.execute("INSERT INTO source.load_log VALUES (?,?,?,?,?,?,?,?,?)", scn, as_of, run_ts, end, len(rows), n_upd, 0, len(ref_changed), n_ob)
    conn.commit()
    return dict(scenario=scn, as_of=str(as_of), watermark_ts_utc=str(run_ts), trades_inserted=len(rows), trades_updated=n_upd,
                updates_by_kind={k: len(v) for k, v in touched.items() if k != "new"}, ref_rows_updated=len(ref_changed),
                ref_changes=ref_changed, outbox_rows=n_ob, new_trade_range=[touched["new"][0], touched["new"][-1]],
                late_update_trades=touched["late"])


def status(conn):
    cur = conn.cursor()
    cur.execute("SELECT scenario, as_of_date, run_start_ts, trades_inserted, trades_updated, ref_updated, outbox_rows FROM source.load_log ORDER BY scenario")
    rows = cur.fetchall()
    print("scenario  as_of       run_start_utc        trades+  trades~  ref~  outbox")
    for x in rows:
        print("%-8s  %s  %s  %7d  %7d  %4d  %6d" % (x[0], x[1], str(x[2])[:19], x[3], x[4], x[5], x[6]))
    for q, lab in [("SELECT COUNT(*) FROM source.trades", "trades"), ("SELECT COUNT(*) FROM source.trade_event_outbox", "outbox events")]:
        cur.execute(q); print(lab, cur.fetchone()[0])
    cur.execute("SELECT trade_status, COUNT(*) FROM source.trades GROUP BY trade_status ORDER BY 2 DESC")
    print("status:", {a: b for a, b in cur.fetchall()})


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    ctx = Ctx()
    conn = sqlconn.connect()
    if cmd == "status":
        return status(conn)
    res = d0(ctx, conn) if cmd == "d0" else increment(ctx, conn, cmd)
    p = os.path.join(config.evidence_dir("source_manifests"), "sql_%s.json" % cmd)
    json.dump(res, open(p, "w"), indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
