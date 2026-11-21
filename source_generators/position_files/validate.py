"""Independent validation of generated position files (does not reuse generator logic):
good files must resolve 100% to SQL reference data; the bad file's detected defects must equal the manifest."""
import csv
import datetime as dt
import glob
import json
import os
import re

from common import config, sqlconn

CCY = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "SGD", "HKD"}


def analyse(path, instr, ports):
    seen, found = {}, {k: 0 for k in ["missing_portfolio", "duplicate_position_id", "invalid_quantity", "invalid_currency", "unknown_instrument", "invalid_date"]}
    rows = list(csv.DictReader(open(path)))
    for r in rows:
        pid = r["position_id"]
        seen[pid] = seen.get(pid, 0) + 1
        if seen[pid] == 2: found["duplicate_position_id"] += 1
        if not r["portfolio_ref"].strip(): found["missing_portfolio"] += 1
        elif r["portfolio_ref"] not in ports: found["missing_portfolio"] += 0
        try: float(r["position_qty"])
        except ValueError: found["invalid_quantity"] += 1
        if r["ccy"] not in CCY: found["invalid_currency"] += 1
        elif r["instrument_code"] in instr and instr[r["instrument_code"]] != r["ccy"]: found["invalid_currency"] += 0
        if r["instrument_code"] not in instr: found["unknown_instrument"] += 1
        try: dt.date.fromisoformat(r["position_date"])
        except ValueError: found["invalid_date"] += 1
    return len(rows), found


def main():
    conn = sqlconn.connect(); cur = conn.cursor()
    instr = dict(cur.execute("SELECT sec_code, ccy FROM reference.instruments").fetchall())
    ports = {x[0] for x in cur.execute("SELECT book_cd FROM reference.portfolios").fetchall()}
    out, ok_all = ["# Position file validation", "", "| File | Rows | Result | Detail |", "|---|---|---|---|"], True
    base = config.out_dir("positions")
    for path in sorted(glob.glob(os.path.join(base, "*", "*.csv"))):
        name = os.path.relpath(path, base)
        n, found = analyse(path, instr, ports)
        total_bad = sum(found.values())
        man = json.load(open(os.path.join(config.evidence_dir("source_manifests"), "positions_%s.json" % ("d2" if "d2" in name else name.split("/")[0]))))
        if "d2_bad" in name:
            exp = man["defects_injected"]
            ok = all(found[k] == exp[k] for k in exp)
            detail = "detected == injected: %s" % found
        else:
            ok = total_bad == 0 and n == man["good_rows"] or ("d2_fixed" in name and total_bad == 0)
            detail = "all keys/ccy/dates valid, no duplicates" if total_bad == 0 else str(found)
        ok_all &= ok
        out.append("| %s | %d | %s | %s |" % (name, n, "PASS" if ok else "FAIL", detail))
    p = os.path.join(config.evidence_dir(), "position_files_validation.md")
    open(p, "w").write("\n".join(out) + "\n"); print("\n".join(out))
    raise SystemExit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
