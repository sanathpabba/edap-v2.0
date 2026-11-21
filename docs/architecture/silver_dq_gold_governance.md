# Silver, Data Quality, Gold and Governance (design as built, not yet run)

Everything below is driven by YAML in `definitions/`; the code in `edap_framework/` contains no entity-, table- or column-specific logic
(the one exception is the registered `fx_flatten` transform, referenced by name from `mappings/market_data.yml`).

## Flow and run order
`pipelines/run.py` : Common (landing, bronze, silver incl. reference data, gold) -> each asset class (bronze -> silver -> gold) -> `runners/governance_apply.py`. Table names carry the pipeline prefix, e.g. `edap.silver.equities_trade`, `edap.gold.fixed_income_pnl_finance`; shared entities are `common_*`. See [pipelines.md](pipelines.md).

| Step | YAML | Code | Output |
|---|---|---|---|
| Reference data | `reference_data/*.yml` (currency, trade_status, instrument_classification, country_region, counterparty_rating) | `silver/reference.py` | `edap.reference.*` with effective dates, active flag, version, owner, source; new version closes old rows |
| DQX at Bronze | `dq_rules/bronze/*.yml` (9 rule sets) | `dq/engine.py`, `dq/bronze_check.py` | bad rows copied to `edap.quarantine.bronze_invalid`; Bronze itself keeps every row |
| Silver | `mappings/*.yml` (instrument, portfolio, counterparty, account, trade, trade_event, position, market_data) | `silver/engine.py` | `edap.silver.<entity>` (incremental by Bronze `_ingest_ts`, dedup, lookups, DQX, MERGE) |
| DQX at Silver | `dq_rules/silver/*.yml` (8 rule sets) | same engine | `edap.quarantine.silver_invalid` |
| Gold | `gold_products/*.yml` (fx_rate_daily + 4 products) | `gold/builder.py` | `edap.gold.*`, documented with UC comments/tags; flag-mode DQX expectations |
| Governance | `governance/*.yml` | `governance/apply.py` | tags/comments, grants, column mask, lineage report, record trace |

## Data quality (DQX)
Rules are standard DQX metadata checks (`function`/`arguments`/`criticality`). `error` -> row quarantined, `warn` -> row passes and is recorded.
Per run: `monitoring.dq_results` (one row per rule, including rules that found nothing), `monitoring.dq_summary` (pass rate), quarantine rows with
`failed_rules`, full record JSON, status and resolution. Bronze-quarantined rows are excluded from Silver by `_row_hash`. A corrected file resend
(same business date, higher version) closes the earlier version's quarantine rows as `SUPERSEDED_BY_RESEND`, and Silver's MERGE lets the newer file version win.
Mapping of injected defects to rules: the six position-file defects -> `file_positions` rules (all but `unknown_instrument`, which is Silver `instrument_resolves`);
the six malformed event types -> `stream_trade_events` rules (all but `unknown_trade`, which is Silver `trade_resolves`).

## Silver behaviour worth knowing
- Late/older versions never overwrite newer data (`update_when` compares source timestamps / file versions); events are immutable (first copy wins).
- FX: history and daily envelopes are flattened to one row per date and currency, USD=1 added; a non-stale pull beats a stale one for the same date.
- Lineage columns: `_bronze_file`, `_bronze_batch_id`, `_landing_batch_id`, `_bronze_row_hash`, `_silver_batch_id`, `_run_id`, `_spec_path`, `_spec_version`.

## Gold products
| Product | Grain | Notes |
|---|---|---|
| `fx_rate_daily` (conformed dimension) | rate_date x currency | gap-free USD rate; weekends carry the last rate; every product converts through it |
| `trade_analytics` | one row per trade | enriched with instrument/portfolio/counterparty/account, USD amounts, days to settle |
| `position_exposure` | position_date x portfolio x instrument | USD market value, cost basis, portfolio weight |
| `pnl_finance` | position_date x portfolio | unrealised P&L, trading costs, P&L after costs |
| `regulatory_reporting` | reporting_date x counterparty | notional, fail rate, large-exposure flag (threshold is a YAML parameter), versioned |

## Governance (Phase 14)
UC comments/tags for catalog and all ten schemas (`ownership.yml`); personas and grants (`access.yml`) with one denied-access demo
(analyst queries `regulatory_reporting`); LEI column mask (`masking.yml`); lineage path report from `system.access.table_lineage`
(`lineage_report`) and a record trace (`trace_record`) that follows one trade/position/event from Gold-ready Silver back to its Bronze row, landing batch and runs.
Prerequisite: the four personas must exist as account-level groups.

## Status
Written and parse-checked only; nothing executed against Databricks. Known assumptions to confirm at first run: DQX 0.17 check names/argument
shapes (as exercised in the Phase 0 feasibility test), `last_value(..., true)` window and `GRANT`/mask syntax on the v2-0 workspace,
and that position `avg_cost` is in the position's own currency.
