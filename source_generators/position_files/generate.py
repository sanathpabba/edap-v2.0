"""Daily position extract generator (file source).
Positions are derived from the SQL trades at the time of generation (net qty of executed/settled trades by
portfolio+instrument), so files always join to reference data and reconcile to trades.
  python -m position_files.generate d0|d1|d2
d0/d1 -> good file; d2 -> a BAD file (defects injected) plus the corrected re-send (_v2)."""
import csv
import hashlib
import json
import os
import random
import sys
from collections import defaultdict

from common import config, sqlconn
from azure_sql.generate import Ctx

COLS = ["position_id", "position_date", "portfolio_ref", "instrument_code", "position_qty", "avg_cost", "market_value", "ccy", "source_system"]


def build_rows(ctx, conn, as_of):
    cur = conn.cursor()
    cur.execute("""SELECT book_cd, sec_code, side, qty, price FROM source.trades
                   WHERE trade_dt <= ? AND trade_status IN ('EXECUTED','SETTLED')""", as_of)
    net, buys, sells = defaultdict(float), defaultdict(lambda: [0.0, 0.0]), defaultdict(lambda: [0.0, 0.0])
    for pf, sc, side, q, p in cur.fetchall():
        q, p = float(q), float(p)
        k = (pf, sc)
        net[k] += q if side == "BUY" else -q
        tgt = buys if side == "BUY" else sells
        tgt[k][0] += q * p; tgt[k][1] += q
    rows = []
    for (pf, sc), q in sorted(net.items()):
        if abs(q) < 1e-9:
            continue
        ins = ctx.ins[sc]
        src = buys if q > 0 else sells
        cost = src[(pf, sc)][0] / src[(pf, sc)][1] if src[(pf, sc)][1] else ctx.pb.price(sc, as_of)
        mv = q * ctx.pb.price(sc, as_of) * float(ins["contract_size"])
        rows.append([pf, sc, "%.4f" % q, "%.6f" % cost, "%.2f" % mv, ins["ccy"]])
    stamp = as_of.strftime("%Y%m%d")
    return [["POS-%s-%04d" % (stamp, i), as_of.isoformat(), r[0], r[1], r[2], r[3], r[4], r[5], "PORTFOLIO_SYS"] for i, r in enumerate(rows, 1)]


def inject_defects(rows, cfg, as_of):
    r = random.Random(cfg["seed"] + 77)
    spec = cfg["position_file_defects"]
    idx = list(range(len(rows))); r.shuffle(idx)
    out = [list(x) for x in rows]
    manifest, cur = {}, 0
    def take(n):
        nonlocal cur
        sel = idx[cur:cur + n]; cur += n
        return sel
    for k in take(spec["missing_portfolio"]):
        manifest.setdefault("missing_portfolio", []).append(out[k][0]); out[k][2] = ""
    for k in take(spec["duplicate_position_id"]):
        src = out[(k + 1) % len(out)][0]
        manifest.setdefault("duplicate_position_id", []).append("%s (copy of %s)" % (out[k][0], src)); out[k][0] = src
    for k in take(spec["invalid_quantity"]):
        manifest.setdefault("invalid_quantity", []).append(out[k][0]); out[k][4] = r.choice(["N/A", "abc", "1,5O0", "--"])
    for k in take(spec["invalid_currency"]):
        manifest.setdefault("invalid_currency", []).append(out[k][0]); out[k][7] = r.choice(["XXX", "US", "euro", "123"])
    for n, k in enumerate(take(spec["unknown_instrument"])):
        manifest.setdefault("unknown_instrument", []).append(out[k][0]); out[k][3] = "INST99%03d" % (n + 1)
    for k in take(spec["invalid_date"]):
        manifest.setdefault("invalid_date", []).append(out[k][0]); out[k][1] = r.choice(["2026-13-45", "18/11/2026", "2026-02-30", "not_a_date"])
    return out, manifest


def write(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(COLS); w.writerows(rows)
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def main():
    scn = sys.argv[1]
    ctx = Ctx(); cfg = ctx.cfg
    as_of = cfg["scenario_dates"][scn]
    stamp = as_of.strftime("%Y%m%d")
    conn = sqlconn.connect()
    rows = build_rows(ctx, conn, as_of)
    base = config.out_dir("positions")
    man = {"scenario": scn, "as_of": str(as_of), "good_rows": len(rows)}
    if scn in ("d0", "d1"):
        p = os.path.join(base, scn, "positions_%s.csv" % stamp)
        man["files"] = {os.path.basename(p): {"rows": len(rows), "sha256_16": write(p, rows), "kind": "good"}}
    else:
        bad, defects = inject_defects(rows, cfg, as_of)
        pb = os.path.join(base, "d2_bad", "positions_%s.csv" % stamp)
        pf = os.path.join(base, "d2_fixed", "positions_%s_v2.csv" % stamp)
        man["files"] = {os.path.basename(pb): {"rows": len(bad), "sha256_16": write(pb, bad), "kind": "bad", "folder": "d2_bad"},
                        os.path.basename(pf): {"rows": len(rows), "sha256_16": write(pf, rows), "kind": "corrected re-send", "folder": "d2_fixed"}}
        man["defects_injected"] = {k: len(v) for k, v in defects.items()}
        man["defect_rows"] = defects
    mp = os.path.join(config.evidence_dir("source_manifests"), "positions_%s.json" % scn)
    json.dump(man, open(mp, "w"), indent=2)
    print(json.dumps({k: v for k, v in man.items() if k != "defect_rows"}, indent=2))


if __name__ == "__main__":
    main()
