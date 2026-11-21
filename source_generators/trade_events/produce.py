"""Publish trade lifecycle events from the SQL outbox to Azure Event Hubs.
  python -m trade_events.produce d0|d1|d2 [--dry-run]
Controlled anomalies (seeded, counted in the manifest): duplicates, out-of-order delivery, late-arriving events
(held back and sent with the next scenario), malformed messages. Uses the send-only Event Hubs policy from Key Vault."""
import datetime as dt
import json
import os
import random
import sys

from common import config, secrets, sqlconn

HEAD = "SELECT event_id,trade_no,event_type,event_ts,sec_code,book_cd,cpty_code,side,qty,price,ccy,scenario FROM source.trade_event_outbox"


def payload(x):
    return {"event_id": x[0], "trade_id": x[1], "instrument_id": x[4], "portfolio_id": x[5], "counterparty_id": x[6],
            "trade_type": x[7], "quantity": float(x[8]), "price": float(x[9]), "currency": x[10], "event_type": x[2],
            "event_timestamp": x[3].strftime("%Y-%m-%dT%H:%M:%S") + "Z"}


def malformed(r, k, scn, base):
    kinds = ["missing_trade_id", "bad_timestamp", "negative_quantity", "not_json", "unknown_event_type", "unknown_trade"]
    kind = kinds[k % len(kinds)]
    p = dict(base); p["event_id"] = "EVT9%07d" % (int(scn[1]) * 1000 + k)
    if kind == "missing_trade_id": p.pop("trade_id")
    elif kind == "bad_timestamp": p["event_timestamp"] = "yesterday-ish"
    elif kind == "negative_quantity": p["quantity"] = -abs(p["quantity"])
    elif kind == "unknown_event_type": p["event_type"] = "TRADE_TELEPORTED"
    elif kind == "unknown_trade": p["trade_id"] = "TRD9999%03d" % k
    body = "this is not json {{{" if kind == "not_json" else json.dumps(p)
    return kind, body, p.get("trade_id", "none")


def main():
    scn = sys.argv[1]; dry = "--dry-run" in sys.argv
    cfg = config.load(); ev = cfg["events"]; r = random.Random(cfg["seed"] + {"d0": 3, "d1": 4, "d2": 5}[scn])
    conn = sqlconn.connect(); cur = conn.cursor()
    cur.execute(HEAD + " WHERE published_ts IS NULL AND scenario <= ? ORDER BY event_ts", scn)
    rows = cur.fetchall()
    carried = [x for x in rows if x[11] < scn]
    fresh = [x for x in rows if x[11] == scn]
    held = []
    if scn != "d2":      # hold back a share of fresh events; they arrive with the next scenario => genuinely late-arriving
        k = int(len(fresh) * ev["late_arriving_rate"]); idx = set(r.sample(range(len(fresh)), k))
        held = [fresh[i] for i in sorted(idx)]
        fresh = [x for i, x in enumerate(fresh) if i not in idx]
    send = carried + fresh
    msgs = [(x[1], json.dumps(payload(x)), x[0]) for x in send]           # (partition key, body, event_id)
    # out-of-order: move a share of messages 5..60 positions later
    n_ooo = int(len(msgs) * ev["out_of_order_rate"])
    for i in r.sample(range(len(msgs) - 70), n_ooo):
        msgs.insert(i + r.randint(5, 60), msgs.pop(i))
    # duplicates
    dups = r.sample(range(len(msgs)), int(len(msgs) * ev["duplicate_rate"]))
    for i in sorted(dups, reverse=True):
        msgs.insert(i + r.randint(1, 30), (msgs[i][0], msgs[i][1], msgs[i][2]))
    # malformed (synthetic, not in outbox)
    base = payload(send[0]) if send else {}
    mal = {}
    for k in range(ev["malformed_count"][scn]):
        kind, body, key = malformed(r, k, scn, base); mal[kind] = mal.get(kind, 0) + 1
        msgs.insert(r.randint(0, len(msgs)), (key, body, "MALFORMED"))
    man = {"scenario": scn, "dry_run": dry, "outbox_rows_published": len(send), "of_which_carried_from_previous_scenario(late)": len(carried),
           "held_back_for_next_scenario": len(held), "duplicates_sent": len(dups), "out_of_order_moved": n_ooo,
           "malformed_sent": mal, "total_messages_sent": len(msgs)}
    if not dry:
        from azure.eventhub import EventHubProducerClient, EventData
        prod = EventHubProducerClient.from_connection_string(secrets.get("eventhub-send-connection-string"))
        with prod:
            batch, sent = prod.create_batch(), 0
            for key, body, _ in msgs:
                try: batch.add(EventData(body))
                except ValueError:
                    prod.send_batch(batch); sent += len(batch); batch = prod.create_batch(); batch.add(EventData(body))
            if len(batch): prod.send_batch(batch); sent += len(batch)
        man["sent_confirmed"] = sent
        pub_ts = dt.datetime.utcnow().replace(microsecond=0)
        ids = [(pub_ts, x[0]) for x in send]
        cur.fast_executemany = True
        cur.executemany("UPDATE source.trade_event_outbox SET published_ts=? WHERE event_id=?", ids)
        conn.commit()
    p = os.path.join(config.evidence_dir("source_manifests"), "events_%s%s.json" % (scn, "_dryrun" if dry else ""))
    json.dump(man, open(p, "w"), indent=2); print(json.dumps(man, indent=2))


if __name__ == "__main__":
    main()
