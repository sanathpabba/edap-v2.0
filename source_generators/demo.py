"""One-command demo driver for the four source systems.
  ./run.sh demo.py d0|d1|d2     apply that scenario to all four sources (SQL, position files, FX, events)
  ./run.sh demo.py fix-d2       send the corrected position file (after the bad file was quarantined)
  ./run.sh demo.py stale-fx     pull FX for a weekend date => stale-data case
  ./run.sh demo.py status       what exists right now
  ./run.sh demo.py verify [d0|d1|d2]   cross-source verification report
  ./run.sh demo.py reset --yes  DESTRUCTIVE: clears landing files and recreates the Event Hubs hub, then run d0
"""
import glob
import os
import shutil
import subprocess
import sys

from common import config, landing, secrets

PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))


def run(*mod):
    print("  $", " ".join(mod))
    r = subprocess.run([PY, "-m"] + list(mod), cwd=HERE, env=dict(os.environ, PYTHONPATH=HERE))
    if r.returncode:
        sys.exit("step failed: %s" % " ".join(mod))


def recreate_hub():
    ns, rg, kv = "edap-eventhubs-645ca5", "edap-rg", "edap-kv-b777d5"
    az = lambda *a: subprocess.run(["az"] + list(a), capture_output=True, text=True)
    az("eventhubs", "eventhub", "delete", "-g", rg, "--namespace-name", ns, "--name", "trade-events")
    r = az("eventhubs", "eventhub", "create", "-g", rg, "--namespace-name", ns, "--name", "trade-events",
           "--partition-count", "4", "--cleanup-policy", "Delete", "--retention-time-in-hours", "168")
    if r.returncode:
        sys.exit("hub create failed: " + r.stderr[:200])
    for rule, rights, sec in [("producer-send", "Send", "eventhub-send-connection-string"),
                              ("consumer-listen", "Listen", "eventhub-listen-connection-string")]:
        az("eventhubs", "eventhub", "authorization-rule", "create", "-g", rg, "--namespace-name", ns,
           "--eventhub-name", "trade-events", "--name", rule, "--rights", rights)
        c = az("eventhubs", "eventhub", "authorization-rule", "keys", "list", "-g", rg, "--namespace-name", ns,
               "--eventhub-name", "trade-events", "--name", rule, "--query", "primaryConnectionString", "-o", "tsv").stdout.strip()
        az("keyvault", "secret", "set", "--vault-name", kv, "--name", sec, "--value", c)
    secrets._cache.clear()


def upload_all(pattern, remote_dir):
    for f in sorted(glob.glob(pattern)):
        landing.upload(f, "%s/%s" % (remote_dir, os.path.basename(f)))
        print("  uploaded", remote_dir + "/" + os.path.basename(f))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    base = config.out_dir()
    if cmd == "reset":
        if "--yes" not in sys.argv:
            sys.exit("reset is destructive (clears landing files, recreates the Event Hubs hub). Re-run with --yes.")
        for d in ("positions", "fx_rates"):
            shutil.rmtree(os.path.join(base, d), ignore_errors=True)
            for sub in ("inbound", "processed", "archive", "quarantine"):
                landing.clear("%s/%s" % (d, sub))
        recreate_hub()
        print("reset done; SQL is reset by running d0")
    elif cmd == "d0":
        run("azure_sql.generate", "d0"); run("position_files.generate", "d0"); run("fx_rates.fetch", "d0"); run("trade_events.produce", "d0")
        upload_all(os.path.join(base, "positions", "d0", "*.csv"), "positions/inbound")
        upload_all(os.path.join(base, "fx_rates", "fx_rates_history_*.json"), "fx_rates/inbound")
    elif cmd == "d1":
        run("azure_sql.generate", "d1"); run("position_files.generate", "d1"); run("fx_rates.fetch", "d1"); run("trade_events.produce", "d1")
        upload_all(os.path.join(base, "positions", "d1", "*.csv"), "positions/inbound")
        upload_all(os.path.join(base, "fx_rates", "fx_rates_20261117.json"), "fx_rates/inbound")
    elif cmd == "d2":
        run("azure_sql.generate", "d2"); run("position_files.generate", "d2"); run("fx_rates.fetch", "d2"); run("trade_events.produce", "d2")
        upload_all(os.path.join(base, "positions", "d2_bad", "*.csv"), "positions/inbound")   # the BAD file arrives
        upload_all(os.path.join(base, "fx_rates", "fx_rates_20261118.json"), "fx_rates/inbound")
    elif cmd == "fix-d2":
        upload_all(os.path.join(base, "positions", "d2_fixed", "*.csv"), "positions/inbound")
    elif cmd == "stale-fx":
        run("fx_rates.fetch", "stale"); upload_all(os.path.join(base, "fx_rates", "*_stale.json"), "fx_rates/inbound")
    elif cmd == "status":
        run("azure_sql.generate", "status")
        for d in ("positions", "fx_rates"):
            for sub in ("inbound", "processed", "archive", "quarantine"):
                fl = landing.list_files("%s/%s" % (d, sub))
                if fl:
                    print("landing/%s/%s: %s" % (d, sub, ", ".join(os.path.basename(x) for x in fl)))
    elif cmd == "verify":
        run("azure_sql.validate", sys.argv[2] if len(sys.argv) > 2 else "d2"); run("position_files.validate"); run("verify_sources")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
