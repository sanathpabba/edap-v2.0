# Landing and Bronze (design as built, not yet run)

> Updated: layout, naming and execution are now per asset class; see [pipelines.md](pipelines.md). The table below shows the source-level view.

Each source system is processed on its own: its own definitions folder, its own runner, its own tables.

| Source | Landing spec | Bronze spec | Landing runner | Landing result (ADLS `landing`) | Bronze table |
|---|---|---|---|---|---|
| Azure SQL (5 tables) | `definitions/landing/sql-loads/<table>.yml` | `definitions/bronze/sql-loads/<table>.yml` | Common/landing steps | `sql/<table>/ingest_date=../batch_id=../*.parquet` | `edap.bronze.sql_<table>` |
| Position files | `.../file-loads/positions.yml` | `.../file-loads/positions.yml` | Common/landing steps | `positions/inbound/*.csv` (registered in `edap.audit.file_arrivals`) | `edap.bronze.file_positions` |
| Trade events | `.../stream-loads/trade_events.yml` | `.../stream-loads/trade_events.yml` | Common/landing steps | `events/trade_events/ingest_date=../*.json` | `edap.bronze.stream_trade_events` |
| FX REST API | `.../api-loads/fx_rates.yml` | `.../api-loads/fx_rates.yml` | Common/landing steps | `fx_rates/inbound/*.json` | `edap.bronze.api_fx_rates` |

Bronze: `python pipelines/run.py --asset-class <X> --layer bronze --mode Routine` (see pipelines.md; table names are now `edap.bronze.<prefix>_<source>_<table>`).

## Rules
- **Landing** = raw files exactly as the source gave them. SQL extracts are full on the first run, watermark deltas after; the
  watermark (`edap.metadata.watermarks`) advances only after the files are written. Every run writes `edap.audit.ingestion_runs`.
- **Bronze** = append-only Delta, Auto Loader `availableNow` (incremental by file), audit columns (`_source_system`, `_source_object`,
  `_batch_id`, `_ingest_ts`, `_ingest_date`, `_source_file`). No cleansing, no dedup, no renaming (legacy names stay; Silver maps them).
  Positions are all strings; events keep `raw_value` plus a permissive typed parse; FX keeps the raw response JSON.
- DQX rule files (`definitions/dq_rules/bronze/*.yml`) are referenced by each spec with `mode: later`; authored in the DQ phase.
- Specs hold no secrets; secrets come from the Key Vault-backed scope `edap-kv` by logical name (`definitions/environments/dev.yml`).

## Lineage metadata (on every Bronze row)
`_source_system`, `_source_object`, `_source_file` (exact landing file), `_landing_batch_id` (from the landing path for SQL/events,
from the file registry for files/FX), `_batch_id` (this Bronze batch), `_run_id` (Databricks job run, passed as `--run-id {{job.run_id}}`),
`_row_hash` (sha256 of the source columns), `_spec_path` + `_spec_version` (the YAML that produced the row), `_ingest_ts`, `_ingest_date`.
Each Bronze table also gets a Unity Catalog comment and tags (layer, source_system, owner, sensitivity, spec) from its `governance` block.
Table/column lineage itself is captured by Unity Catalog; these columns add the run-level and file-level links UC cannot infer.

## Status
Written and reviewed for consistency only. Nothing has been executed or validated against Databricks yet (by request).
Needs before first run: UC external locations for the `landing`/`bronze` containers, schemas `edap.audit`/`edap.metadata`,
and `pyyaml`/`requests` in the job environment.
