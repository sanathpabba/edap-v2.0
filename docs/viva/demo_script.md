# 20-minute viva demo script (draft)

Pre-requisites: Databricks pipeline validated; dashboard (Consumption phase) built. Commands refer to `runners/` and `source_generators/`.

| Min | Step | Show | Command / place |
|---|---|---|---|
| 0-2 | Problem and approach | 1.0 failures, YAML-driven modular framework, layer diagram | slides |
| 2-4 | The four sources | SQL (reference + trades), position file, Event Hubs, FX API; legacy column names on purpose | `source_generators/run.sh demo.py status` |
| 4-7 | **D0 initial load** | Landing files, Bronze tables with lineage columns, row counts | `landing_*`, `bronze_load` ; Catalog Explorer |
| 7-9 | **D1 incremental** | Only changed rows picked (watermark), late events arriving, counts D0 -> D1 | `demo.py d1` then landing/bronze; `edap.metadata.watermarks` |
| 9-12 | **Bad file -> quarantine** | D2 position file with 41 defects: DQX rejects the bad rows, reasons per rule, good rows flow | `demo.py d2`, `dq_bronze --source file-loads`; `edap.quarantine.bronze_invalid` |
| 12-13 | **Fix and reprocess** | Corrected `_v2` file supersedes the quarantined rows | `demo.py fix-d2`, `dq_bronze`, `silver_load --entity position` |
| 13-15 | Silver canonical model | One Trade/Position/Counterparty regardless of source names; reference data; dedup of duplicate events | `silver_load`; `edap.silver.*` |
| 15-17 | Gold data products | Four reusable products, USD via one FX dimension, documentation as catalog comments | `gold_build`; `edap.gold.*` |
| 17-19 | Governance and lineage | UC lineage graph source -> Gold, record trace, denied access, masked LEI | `governance_apply --step trace --entity trade --key TRD0005001` |
| 19-20 | Dashboard and close | Consumption view, reconciliation numbers, what is reusable for other institutions | dashboard |

Backup plan: keep a pre-run copy of every table; evidence screenshots in `docs/dissertation_evidence/`.
