# Source systems: demo scenarios and runbook

All four source systems are driven from `source_generators/` and are reproducible (seed in
`source_generators/config/generation.yml`). Credentials come from Key Vault; nothing is typed or stored locally.

```bash
cd source_generators
./run.sh demo.py d0        # initial load, all four sources
./run.sh demo.py d1        # incremental 1
./run.sh demo.py d2        # incremental 2 (the position file is BAD)
./run.sh demo.py fix-d2    # corrected position file (after the bad file was quarantined)
./run.sh demo.py stale-fx  # weekend FX pull => stale-data case
./run.sh demo.py status    # what exists now
./run.sh demo.py verify d2 # SQL checks + file checks + cross-source/Event Hubs read-back
./run.sh demo.py reset --yes   # DESTRUCTIVE: clears landing files, recreates the Event Hubs hub. Then run d0.
```
`d0` always rebuilds the SQL source from scratch (drop/recreate), so SQL is reset by running `d0`.
Requires `az login`. First-time setup: `python3 -m venv .venv && .venv/bin/pip install pyodbc pyyaml azure-eventhub requests python-dateutil`.

## Business dates
Three consecutive recent business days (past, so real FX rates exist): **D0 = Mon 2026-11-16, D1 = Tue 2026-11-17, D2 = Wed 2026-11-18**.
Source `last_updated_ts` values for D1/D2 changes are the real wall-clock time of the run (that is what a watermark sees).

## What each scenario does (verified counts from the last run)
| | Azure SQL | Position file | Event Hubs | FX REST |
|---|---|---|---|---|
| **D0 initial** | reference 200 rows (100 instruments, 20 portfolios, 30 accounts, 50 counterparties) + 5,000 trades (as of D0) | `positions_20261116.csv` 1,296 rows | 10,163 outbox events published (+ duplicates, out-of-order, malformed = 10,276 messages); 102 events held back (outbox total 10,265) | history 2024-11-18..2026-11-16 (509 days, 8 currencies vs USD) |
| **D1 incremental** | +120 new trades; 12 existing trades updated (11 lifecycle moves); 5 cancels and 12 amends (mostly on same-day trades); 3 counterparty rating changes | `positions_20261117.csv` 1,305 rows | 225 messages incl. the 102 held-back D0 events (now late-arriving) | daily `fx_rates_20261117.json` |
| **D2 incremental** | +90 new trades; 78 existing trades updated (68 lifecycle moves, 4 cancels, 8 amends, 6 **late corrections to trades > 30 days old**); 2 counterparty changes | **BAD** `positions_20261118.csv` (1,312 rows, 41 injected defects) | 160 messages | daily `fx_rates_20261118.json` |
| **fix-d2** | - | `positions_20261118_v2.csv` (corrected re-send, 1,312 rows) | - | - |
| **stale-fx** | - | - | - | `fx_rates_20261121_stale.json` (requested Sat, API returned Fri => stale) |

D2 bad-file defects (manifest-verified): 10 missing portfolio, 6 duplicate position_id, 8 invalid quantity, 7 invalid currency, 5 unknown instrument, 5 invalid date.

## Where things land
- SQL: `edap-source-db` (`source.*`, `reference.*`); `source.load_log` records each scenario's watermark.
- Files: ADLS `landing/positions/inbound/`, `landing/fx_rates/inbound/` (processed/archive/quarantine folders exist for the pipeline to use).
- Events: Event Hubs `trade-events` (4 partitions, keyed by trade_id), send-only and listen-only policies in Key Vault.
- Evidence: `docs/dissertation_evidence/` (validation reports) and `docs/dissertation_evidence/source_manifests/` (counts per run).

## Design notes (answers to "why is it built this way?")
- **Legacy-style names per source** (SQL `sec_code/book_cd/cpty_code`, file `instrument_code/portfolio_ref/position_qty`, events `instrument_id/portfolio_id`)
  so the canonical mapping in Silver has real work; **values** follow one master ID standard so keys always join.
- **Outbox pattern**: every trade change is also written to `source.trade_event_outbox`; the stream is replayed from it,
  so events and SQL state always agree (verified by the cross-source check).
- **Positions derive from trades** (net executed/settled quantity), so Gold position reconciliation to trades is meaningful.
- **Anomalies are injected in counted, seeded amounts** (manifests) so every DQ/dedup/late-arrival result can be checked against ground truth.
