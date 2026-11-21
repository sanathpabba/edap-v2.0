# EDAP 2.0 - Project Tracker

**Project**: BITS Pilani MBA Business Analytics Dissertation - modular, YAML-driven framework for Capital Markets reporting modernization  
**Approach**: Phase-wise, **source systems first** (initial + incremental load demo), then the metadata-driven framework  
**Last Updated**: 2026-11-21  

## Ground rules

1. **Evidence before DONE.** A task is only marked ✅ with a command, query output or file that proves it (Evidence column). No percentage claims without measured results.
2. **Everything configurable lives in `definitions/` (YAML).** Framework code in `edap_framework/` has no hard-coded source, table or column names.
3. **Synthetic data only; no secrets in code or notebooks** (Key Vault / secret scope).
4. **One master ID standard** across all sources (FND-05) - the main 1.0 failure to avoid.
5. **DQX** is the DQ engine at Bronze and Silver (not custom SQL, not DLT expectations).
6. Finish and verify each phase before starting the next; 1.0 assets are reused only after they pass verification (♻️ REWORK).

## Status overview

| Phase | Name | Tasks | Done | Built, not validated | Rework | Blocked | Todo |
|---|---|---|---|---|---|---|---|
| 0 | Foundation & Decisions | 12 | 12 | 0 | 0 | 0 | 0 |
| 1 | Source 1 - Azure SQL (initial + incremental) | 12 | 12 | 0 | 0 | 0 | 0 |
| 2 | Source 2 - Position Files (good + bad) | 7 | 7 | 0 | 0 | 0 | 0 |
| 3 | Source 3 - Streaming Trade Events | 7 | 7 | 0 | 0 | 0 | 0 |
| 4 | Source 4 - REST FX Rates | 5 | 5 | 0 | 0 | 0 | 0 |
| 5 | Source Systems Demo Pack | 6 | 5 | 0 | 0 | 0 | 1 |
| 6 | YAML Specification & Framework Core | 9 | 0 | 6 | 0 | 0 | 3 |
| 7 | Landing & Bronze (metadata-driven) | 8 | 0 | 6 | 0 | 0 | 2 |
| 8 | Data Quality (DQX) - Bronze & Silver | 6 | 0 | 6 | 0 | 0 | 0 |
| 9 | Silver - Canonical Model & Reference Data | 6 | 0 | 6 | 0 | 0 | 0 |
| 10 | Gold Data Products | 6 | 0 | 6 | 0 | 0 | 0 |
| 11 | Consumption | 3 | 0 | 0 | 0 | 0 | 3 |
| 12 | Orchestration | 4 | 0 | 3 | 0 | 0 | 1 |
| 13 | Monitoring, Audit, Alerting & Cost | 4 | 0 | 0 | 0 | 0 | 4 |
| 14 | Governance, Security & Lineage | 4 | 0 | 4 | 0 | 0 | 0 |
| 15 | Reconciliation & Testing | 5 | 0 | 0 | 0 | 0 | 5 |
| 16 | Deployment | 3 | 0 | 0 | 0 | 0 | 3 |
| 17 | Dissertation Evidence & Viva Demo | 5 | 0 | 2 | 0 | 0 | 3 |
| | **TOTAL** | **112** | **48** | **39** | **0** | **0** | **25** |

**Verified complete: 48/112 tasks.** (Phases 0-5 verified 2026-11-20/21 except SRC-06 evidence capture. Landing/Bronze code is written but deliberately not yet validated.)

## Demo scenario this plan builds toward

| Step | What the audience sees |
|---|---|
| D0 | Initial load: SQL (~5,000 trades + reference), good position file, event burst, FX rates |
| D1 | Incremental: new/updated/cancelled trades (watermark picks only changes), new good file, more events, new FX |
| Defect | Bad position file -> DQX -> quarantine -> alert -> fix -> reprocess |
| Result | Silver canonical entities -> Gold products -> dashboard, with lineage and reconciliation numbers |

## Legends

| Status | Meaning |
|---|---|
| ✅ DONE | Completed and verified (evidence recorded) |
| 🔄 BUILT, NOT VALIDATED | Code/YAML written, not yet run or tested (validation deferred by decision) |
| 📋 TODO | Not started |
| ♻️ REWORK | Exists from 1.0 but failed the audit; fix before reuse |
| ⏸️ BLOCKED | Waiting on a dependency or decision |
| ⏭️ SKIPPED | Deliberately dropped |

Priority: **P0** must-have for the viva demo, **P1** important, **P2** nice-to-have, **P3** stretch.

---

## Phase 0: Foundation & Decisions

_Lock the decisions and environment everything else depends on._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| FND-01 | Azure resources verified | edap-rg: SQL server/db, ADLS (edapdl), Event Hubs, Key Vault, access connector | ✅ DONE | P0 | - | Verified via `az resource list` 2026-11-20 |
| FND-02 | Two Databricks workspaces | v1 serverless-only; v2-0 Hybrid/Premium, same region (centralus) | ✅ DONE | P0 | FND-01 | `az databricks workspace list`: both Succeeded |
| FND-03 | Skills + MCP tooling | Databricks agent skills (34) and Azure MCP installed | ✅ DONE | P1 | - | `~/.claude/skills`, `claude mcp list` shows azure connected |
| FND-04 | Workspace profile for v2-0 | Create CLI profile (OAuth login) so both workspaces are usable with --profile | ✅ DONE | P0 | FND-02 | `databricks current-user me --profile v2` OK; profile v2 (OAuth) in .databrickscfg; v1 OAuth profile also added |
| FND-05 | Master ID standard | One ID format for all sources (adopt SQL: INST00080 / PORT0016 / CPTY0021 / ACC00009 / TRD0000001) | ✅ DONE | P0 | - | docs/architecture/decisions.md (D1): SQL ID format is the master standard |
| FND-06 | Catalog & schema naming | Decide catalog name (edip vs edap) and schema list; settle Platinum vs Consumption | ✅ DONE | P0 | - | decisions.md (D2): catalog 'edap' (free; 1.0 'edap_prod' untouched), Consumption layer, 10 schemas; metastore shared by both workspaces |
| FND-07 | Secrets handling | Move SQL password, EH connection string, tokens to Key Vault / Databricks secret scope; remove plaintext from env files and notebooks | ✅ DONE | P0 | FND-04 | 8 secrets in Key Vault edap-kv-b777d5; Databricks scope 'edap-kv' (Azure-backed) verified listing 8 keys; read test in job returned secret; plaintext env files removed; password redacted from docs |
| FND-08 | Revoke exposed Databricks token | PAT 'bits-token' was pasted in chat history; replaced by OAuth profiles | ✅ DONE | P0 | FND-04 | User revoked PAT ( empty); DEFAULT/v1/v2 all authenticate via OAuth; no token lines in .databrickscfg. Remaining: chat.json still holds the (now dead) token - git-ignored |
| FND-12 | Rotate SQL admin password & Event Hubs root key | Both appeared in plaintext in 1.0 files/chat; rotated via repeatable script, stored only in Key Vault | ✅ DONE | P1 | FND-07 | infra/rotate_secrets.sh all: new SQL password works and old is rejected; both EH keys renewed; Key Vault shows version 2 tagged rotated=2026-11-21T00:18:57Z; Databricks scope shows updated timestamps; runbook docs/runbooks/secret_rotation.md |
| FND-09 | Git repo for 2.0 | Initialise repo, .gitignore, connect remote, first commit | ✅ DONE | P1 | - | git repo on main, commit c6e6e1a; .gitignore excludes .databrickscfg, config/*.env, chat.json; secret scan clean |
| FND-10 | DQX feasibility | Install databricks-labs-dqx on v2-0 runtime; run one YAML check end-to-end | ✅ DONE | P0 | FND-04 | Serverless job on v2-0: DQX 0.17.2 installs; YAML rules via apply_checks_by_metadata_and_split -> 3 valid / 4 quarantined of 5; is_in_list needs quoted literals or sql_expression; warn rows appear in both outputs |
| FND-11 | Reconcile env files | Single clean env config (region, duplicates, empty KEY_VAULT_URI) | ✅ DONE | P2 | FND-07 | config/azure.env (no secrets, values read from Azure); secrets referenced by Key Vault name; infra/get_secret.sh |

---

## Phase 1: Source 1 - Azure SQL (initial + incremental)

_Repair the SQL source and make initial and incremental loads demonstrable._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| SQL-01 | Schema review vs spec | Compare 1.0 tables with the spec: add trade currency, check watermark columns | ✅ DONE | P0 | FND-05 | Spec gaps closed in DDL (trade_ccy, last_updated_ts watermarks, outbox); source_generators/azure_sql/ddl/01_schema_and_tables.sql |
| SQL-02 | Idempotent DDL scripts | Rewrite/verify create-schema, tables, constraints, indexes; safe to re-run | ✅ DONE | P0 | SQL-01 | DDL drops/recreates idempotently; d0 re-run during the 2026-11-20 rebuild succeeded |
| SQL-03 | Reference data redesign | Instruments (type-consistent price/currency/exchange), portfolios, accounts, counterparties on the master ID standard | ✅ DONE | P0 | FND-05 | 100 instruments/20 portfolios/30 accounts/50 counterparties on master IDs; validate.py ID-format checks 0 violations |
| SQL-04 | Account-portfolio consistency | Fix 582 trades whose account belongs to a different portfolio | ✅ DONE | P0 | SQL-03 | Check 'trade account belongs to trade portfolio' = 0 mismatches (1.0 had 582); docs/dissertation_evidence/sql_validation_d2.md |
| SQL-05 | Realistic trade lifecycle | Statuses/types follow a believable lifecycle (NEW->EXECUTED->SETTLED; amend/cancel link to an original trade) | ✅ DONE | P0 | SQL-03 | Lifecycle + status-mix + 'no event precedes execution' checks pass; defect found and fixed by verification (later()) |
| SQL-06 | Realistic prices & notionals | Price/quantity depend on instrument type; add trade currency | ✅ DONE | P1 | SQL-03 | Prices within 2% of daily market price (0 of 4,901 outside); max notional USD 20.6M; trade_ccy = instrument ccy |
| SQL-07 | Initial load (D0) | Generate ~5,000 trades + reference data from the generator (seeded, reproducible) | ✅ DONE | P0 | SQL-02..06 | D0: 5,000 trades; sql_validation_d0.md 22/22 |
| SQL-08 | Incremental scenario (D1) | Generator applies inserts + updates + cancels with new last_updated_ts; known counts | ✅ DONE | P0 | SQL-07 | D1: +120 new trades; sql_validation_d1.md 23/23; watermark delta found 65 rows after rebuild (<= 132 bound) |
| SQL-09 | Incremental scenario (D2) | Second increment incl. late update to an old trade (late-arriving case) | ✅ DONE | P1 | SQL-08 | D2: +90 new, 78 updated, incl. 6 late corrections to trades > 30 days old; watermark delta 168 = expected; 25/25 |
| SQL-10 | Validation script | Repeatable checks: counts, FKs, nulls, domains, arithmetic, watermark coverage | ✅ DONE | P0 | SQL-07 | azure_sql/validate.py: 25 checks at D2 all PASS; reports in docs/dissertation_evidence/ |
| SQL-11 | Generator under source_generators/ | Config-driven (YAML) generator, seed, volumes, scenario switch D0/D1/D2 | ✅ DONE | P1 | SQL-07 | source_generators/ (seed 20261116, config/generation.yml, d0/d1/d2 switch) |
| SQL-12 | Source README + runbook | How to reset, load D0, apply D1/D2, validate | ✅ DONE | P1 | SQL-10 | docs/runbooks/demo_scenarios.md (counts need refresh after rebuild) |

---

## Phase 2: Source 2 - Position Files (good + bad)

_Daily position extracts on the master ID standard with deliberate defects._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| FILE-01 | File schema (YAML) | Position CSV schema as a definition file | ✅ DONE | P0 | FND-05 | definitions/sources/positions_file.yml |
| FILE-02 | Generator from real keys | Generate positions from the actual SQL reference keys (~2,000 rows total) | ✅ DONE | P0 | SQL-07 | Positions derived from SQL trades; keys validated against SQL reference data |
| FILE-03 | Good files D0/D1 | positions_YYYYMMDD.csv for initial and next day | ✅ DONE | P0 | FILE-02 | positions_20261116.csv (1,296 rows), positions_20261117.csv (1,305 rows); position_files_validation.md PASS |
| FILE-04 | Bad file with all defect types | Missing portfolio, duplicate position_id, invalid quantity, invalid currency, unknown instrument, invalid date | ✅ DONE | P0 | FILE-02 | D2 bad file: 1,312 rows with 41 defects; independent validator detected == injected (10/6/8/7/5/5); corrected _v2 file also produced |
| FILE-05 | ADLS landing structure | landing/positions/{inbound,processed,archive,quarantine} | ✅ DONE | P0 | FND-01 | landing/positions/{inbound,processed,archive,quarantine} created in ADLS edapdl |
| FILE-06 | Upload scripts | Drop good file / drop bad file into inbound (simulates arrival) | ✅ DONE | P1 | FILE-05 | demo.py d0/d1/d2/fix-d2 upload files to landing/positions/inbound; rebuild run 2026-11-20 uploaded all 4 files |
| FILE-07 | README | File source patterns and demo steps | ✅ DONE | P2 | FILE-06 | Covered in docs/runbooks/demo_scenarios.md |

---

## Phase 3: Source 3 - Streaming Trade Events

_Event Hubs events that tie back to real trades, with lifecycle and defects._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| STR-01 | Event schema (YAML) | Event payload definition (event_id, trade_id, types TRADE_EXECUTED/AMENDED/CANCELLED/SETTLED) | ✅ DONE | P0 | FND-05 | definitions/sources/trade_events.yml |
| STR-02 | Producer from real keys | Events reference real trade/instrument/portfolio IDs; all 9 currencies | ✅ DONE | P0 | SQL-07 | Stream sample: 1,281 of 1,281 messages complete and resolve to SQL trades with matching keys |
| STR-03 | Lifecycle & edge cases | Duplicates, out-of-order, late-arriving, malformed events (controlled counts) | ✅ DONE | P0 | STR-02 | Manifests: duplicates 104, out-of-order 210, malformed 18, late-arriving via held-back events (events_d0..d2.json) |
| STR-04 | Send burst D0 / D1 | Publish initial burst and a later burst to trade-events hub | ✅ DONE | P0 | STR-03 | Producer manifests D0 10,276 / D1 225 / D2 160 = 10,661 messages; Event Hubs IncomingMessages metric matches (since rebuild) |
| STR-05 | Consumer verification | Read back from Event Hubs (Kafka endpoint) to confirm payloads | ✅ DONE | P1 | STR-04 | verify_sources.py bounded sample read via listen policy; full read-back is done by Bronze streaming (Phase 7) |
| STR-06 | Security | Connection string from Key Vault; Send-only/Listen-only policies | ✅ DONE | P1 | FND-07 | Send-only (producer-send) and listen-only (consumer-listen) policies; secrets only in Key Vault |
| STR-07 | README | Streaming source runbook | ✅ DONE | P2 | STR-04 | Covered in docs/runbooks/demo_scenarios.md |

---

## Phase 4: Source 4 - REST FX Rates

_Real FX rates for all instrument/portfolio currencies._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| API-01 | API choice + schema (YAML) | Public no-credential FX API; rate_date, base, quote, rate, source | ✅ DONE | P0 | - | definitions/sources/fx_rates_api.yml (frankfurter.dev, no credentials) |
| API-02 | Currency coverage | Cover AUD, CAD, CHF, EUR, GBP, HKD, JPY, SGD, USD | ✅ DONE | P0 | API-01 | FX history covers all 9 currencies (USD base + 8); cross-source check PASS |
| API-03 | Client with retry/validation | Retry, status check, timestamp, stale-data flag | ✅ DONE | P1 | API-01 | FxClient retry/backoff + payload validation; forced-failure and missing-currency paths tested; stale flag |
| API-04 | Capture raw responses | Save JSON responses (landing) for D0 and D1 dates | ✅ DONE | P0 | API-03 | fx_rates_history (509 days), daily 20261117/20261118, stale weekend file in landing/fx_rates/inbound |
| API-05 | README | API source notes | ✅ DONE | P2 | API-04 | Covered in docs/runbooks/demo_scenarios.md |

---

## Phase 5: Source Systems Demo Pack

_Package all four sources into one repeatable initial + incremental demo._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| SRC-01 | Scenario definition | Define D0 (initial), D1, D2 across all four sources with expected counts | ✅ DONE | P0 | Phases 1-4 | docs/runbooks/demo_scenarios.md |
| SRC-02 | One-command reset | Reset all sources to a clean state | ✅ DONE | P0 | SRC-01 | demo.py reset --yes executed 2026-11-20 (hub recreated, landing cleared) then full rebuild succeeded; reset needed one flag fix |
| SRC-03 | One-command D0 load | Initial load for SQL, files, events, FX | ✅ DONE | P0 | SRC-02 | demo.py d0 executed for all four sources |
| SRC-04 | One-command D1/D2 | Apply incremental changes across sources | ✅ DONE | P0 | SRC-03 | demo.py d1, d2, fix-d2, stale-fx executed |
| SRC-05 | Cross-source consistency check | IDs join across SQL, files, events, FX currencies | ✅ DONE | P0 | SRC-03 | docs/dissertation_evidence/cross_source_verification.md: 8/8 checks pass |
| SRC-06 | Source evidence capture | Screenshots/queries for the dissertation (sources chapter) | 📋 TODO | P1 | SRC-04 | Index of existing evidence in docs/dissertation_evidence/README.md; screenshots/queries still to capture after the first Databricks run |

---

## Phase 6: YAML Specification & Framework Core

_Define the YAML contracts and the core of the modular PySpark framework._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| FWK-01 | YAML schemas | Contracts for source, ingestion, mapping, DQ rules, reference data, Gold product, consumption | 📋 TODO | P0 | FND-05, FND-06 | definitions/ examples validate against schema |
| FWK-02 | Config loader + validator | Load/validate YAML, environment overlays, clear errors | 🔄 BUILT, NOT VALIDATED | P0 | FWK-01 | edap_framework/core/config.py (strict-bool YAML loader) + core/validator.py + runners/validate_definitions.py: 0 errors across 63 YAML files; 15 offline unit tests pass incl. 7 negative cases; environment overlays still to do |
| FWK-03 | Run context | run_id/batch_id, logging, environment | 📋 TODO | P0 | FWK-02 | Unit tests |
| FWK-04 | Metadata/control tables | Source registry, watermark store, run log (UC tables) | 🔄 BUILT, NOT VALIDATED | P0 | FND-06 | Watermark store + run-log helpers written (edap_framework/metadata/watermarks.py, core/audit.py); tables not yet created |
| FWK-05 | Unity Catalog setup | Catalog, schemas, volumes, external locations via script/bundle | 🔄 BUILT, NOT VALIDATED | P0 | FND-06 | deployment/unity_catalog_setup.sql (catalog + 10 schemas); not run |
| FWK-06 | Packaging | Build wheel, install on cluster, import test | 📋 TODO | P1 | FWK-02 | `import edap_framework` on both workspaces |
| FWK-07 | Asset-class pipeline structure | pipelines/<AssetClass>/<bronze|silver|gold>/<Routine|Adhoc>/ for Equities, FixedIncome, FX, Commodities plus Common (landing + shared entities); asset-class YAMLs; ${ac} templating; routing by instrument | 🔄 BUILT, NOT VALIDATED | P0 | FWK-02 | definitions/asset_classes/*.yml, pipelines/ (306 step files), docs/architecture/pipelines.md; 37 offline tests incl. routing/overlap/negative cases; not run on Databricks |
| FWK-08 | Ordinal step files + sequence runner | 8-10 numbered step files per layer, each calling one framework function; pipelines/run.py executes them in order per item; dry-run plan; tools/generate_pipelines.py regenerates the tree | 🔄 BUILT, NOT VALIDATED | P0 | FWK-07 | edap_framework/pipeline/{context,sequence,landing_steps,bronze_steps,silver_steps,gold_steps}.py; dry-run and step-wiring tests pass offline; not run on Databricks |
| FWK-09 | Routine vs Adhoc behaviours | Same steps, mode-aware: Routine incremental/scheduled; Adhoc initial load, backfill, replay (no duplicates), rebuild, what-if parameters | 🔄 BUILT, NOT VALIDATED | P1 | FWK-08 | Documented in docs/architecture/pipelines.md; replay/rebuild logic in bronze/silver/gold step functions; needs a run to verify |

---

## Phase 7: Landing & Bronze (metadata-driven)

_Generic ingestion engine driven by YAML for all four sources._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| BRZ-01 | Generic reader - SQL | JDBC read, full + incremental by watermark | 🔄 BUILT, NOT VALIDATED | P0 | FWK-04 | ingestion/sql/extract.py split into steps (resolve_window, read_extract, write_extract, commit_watermark) + definitions/landing|bronze/sql-loads/*.yml (5 tables); Common/landing steps 01-08; not run |
| BRZ-02 | Generic reader - files | Auto Loader / batch on inbound, file registry | 🔄 BUILT, NOT VALIDATED | P0 | FWK-04 | ingestion/files/arrival.py (scan_arrivals, register_arrivals) + file-loads/positions.yml; Common/landing + asset-class bronze steps; not run |
| BRZ-03 | Generic reader - streaming | Structured Streaming from Event Hubs, checkpoint | 🔄 BUILT, NOT VALIDATED | P0 | FWK-04 | ingestion/streaming/eventhub_to_landing.py (build/write stream; Adhoc replays from earliest) + stream-loads/trade_events.yml; not run |
| BRZ-04 | Generic reader - REST | API pull to landing then Bronze | 🔄 BUILT, NOT VALIDATED | P1 | FWK-04 | ingestion/rest_api/fx_pull.py (fetch_fx, write_fx, register_fx) + api-loads/fx_rates.yml; not run |
| BRZ-05 | Bronze writer + audit columns | Standard _source/_ingestion/_batch/_run/_hash columns | 🔄 BUILT, NOT VALIDATED | P0 | BRZ-01 | bronze/loader.py (read_landing, shape_columns, route_to_asset_class, add_meta_properties, write_bronze) adds _source_system/_source_object/_source_file/_landing_batch_id/_batch_id/_run_id/_row_hash/_spec_path/_spec_version/_ingest_ts/_ingest_date + UC comment and tags from spec; not run |
| BRZ-06 | Schema validation | Expected vs actual schema, drift handling | 📋 TODO | P1 | BRZ-05 | Drift test case |
| BRZ-07 | Idempotency | Re-run does not duplicate | 📋 TODO | P0 | BRZ-05 | Re-run count unchanged |
| BRZ-08 | Onboard a source by YAML only | Add a new table with no code changes | 🔄 BUILT, NOT VALIDATED | P0 | BRZ-01 | runners/scaffold_sql_table.py: generates landing+bronze+starter DQ specs from the source contract; reproduces the 5 existing specs exactly (unit test); docs/runbooks/onboard_new_source_table.md; live onboarding demo still to do |

---

## Phase 8: Data Quality (DQX) - Bronze & Silver

_DQX-based declarative checks from YAML with quarantine._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| DQ-01 | DQ wrapper | Framework function reads dq_rules YAML and applies DQX | 🔄 BUILT, NOT VALIDATED | P0 | FND-10, FWK-01 | edap_framework/dq/engine.py: DQX apply_checks_by_metadata, quarantine + results + summary writers; rule sets in definitions/dq_rules/; not run |
| DQ-02 | Bronze rules | Technical checks per spec | 🔄 BUILT, NOT VALIDATED | P0 | DQ-01 | definitions/dq_rules/bronze/*.yml (9 rule sets, templated per asset class) run as the last Bronze step (bronze_steps.run_dq_and_audit); not run |
| DQ-03 | Silver rules | Business/referential checks | 🔄 BUILT, NOT VALIDATED | P0 | DQ-01 | definitions/dq_rules/silver/*.yml (8 rule sets incl. referential flags from mapping lookups); not run |
| DQ-04 | Quarantine tables | bronze_invalid, silver_invalid with reasons | 🔄 BUILT, NOT VALIDATED | P0 | DQ-01 | edap.quarantine.bronze_invalid / silver_invalid written by the engine with failed_rules, record_json, status; not run |
| DQ-05 | DQ metrics | Rule-level counts and pass/fail summary | 🔄 BUILT, NOT VALIDATED | P1 | DQ-01 | monitoring.dq_results (per rule, incl. zero-failure rules) and monitoring.dq_summary (pass rate) written per run; not run |
| DQ-06 | Remediation + reprocess | Fix and reprocess a quarantined file/record | 🔄 BUILT, NOT VALIDATED | P0 | DQ-04 | dq/quarantine.py close_superseded_by_resend + Silver MERGE on file version; before/after evidence needs a run |

---

## Phase 9: Silver - Canonical Model & Reference Data

_Seven canonical entities driven by mapping YAML._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| SLV-01 | Mapping engine | Source-to-canonical via YAML (rename, cast, lookup, derive) | 🔄 BUILT, NOT VALIDATED | P0 | FWK-01 | silver/engine.py + definitions/mappings/*.yml (columns, lookups, dedup, merge in YAML); not run |
| SLV-02 | Canonical entities | Trade, Instrument, Portfolio, Position, Counterparty, Account, Market Data | 🔄 BUILT, NOT VALIDATED | P0 | SLV-01, BRZ-05 | 8 mappings: instrument, portfolio, counterparty, account, trade, position, market_data (+ trade_event); not run |
| SLV-03 | Reference data | Currency, status, country etc., versioned, effective dates | 🔄 BUILT, NOT VALIDATED | P0 | FWK-05 | definitions/reference_data/*.yml (5 code lists with effective dates/version/owner) + silver/reference.py; not run |
| SLV-04 | Key resolution & dedup | Business-key handling, duplicate events/files | 🔄 BUILT, NOT VALIDATED | P0 | SLV-02 | dedup window per business key in each mapping; quarantined Bronze rows excluded by _row_hash; not run |
| SLV-05 | Late-arriving/updated records | Merge logic for incremental updates | 🔄 BUILT, NOT VALIDATED | P0 | SLV-02, SQL-09 | MERGE update_when guards (newer source ts / file version wins; events immutable); not run |
| SLV-06 | Lineage columns | Source references retained in canonical records | 🔄 BUILT, NOT VALIDATED | P1 | SLV-02 | _bronze_file/_bronze_batch_id/_landing_batch_id/_bronze_row_hash/_silver_batch_id/_run_id/_spec_path on Silver; governance trace_record; not run |

---

## Phase 10: Gold Data Products

_Four reusable products defined in YAML._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| GLD-01 | Product builder | Join/measure/aggregate from product YAML | 🔄 BUILT, NOT VALIDATED | P0 | SLV-02 | gold/builder.py composes SQL from product YAML (CTEs, joins, dimensions, measures, parameters); compose checked offline, not run |
| GLD-02 | Trade Analytics | Reusable trade product | 🔄 BUILT, NOT VALIDATED | P0 | GLD-01 | definitions/gold_products/trade_analytics.yml (grain: trade) |
| GLD-03 | Position & Exposure (with FX) | Market value converted to a common currency | 🔄 BUILT, NOT VALIDATED | P0 | GLD-01, BRZ-04 | definitions/gold_products/position_exposure.yml + conformed fx_rate_daily (USD conversion); totals reconciliation needs a run |
| GLD-04 | P&L / Finance | Finance product | 🔄 BUILT, NOT VALIDATED | P1 | GLD-01 | definitions/gold_products/pnl_finance.yml |
| GLD-05 | Regulatory/Management | Controlled reporting product | 🔄 BUILT, NOT VALIDATED | P1 | GLD-01 | definitions/gold_products/regulatory_reporting.yml (parameterised threshold, versioned) |
| GLD-06 | Product documentation | Purpose, grain, owner, consumers, refresh | 🔄 BUILT, NOT VALIDATED | P1 | GLD-02 | documentation block in every product YAML applied as UC comment/tags; docs/architecture/silver_dq_gold_governance.md |

---

## Phase 11: Consumption

_At least two channels from governed Gold._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| CON-01 | Databricks AI/BI dashboard | Trade and position/exposure views | 📋 TODO | P0 | GLD-03 | Dashboard link + screenshot |
| CON-02 | Second channel | File extract or DB delivery from consumption YAML | 📋 TODO | P0 | GLD-03 | Output file/table produced |
| CON-03 | Power BI (stretch) | Connection to SQL warehouse | 📋 TODO | P2 | CON-01 | Screenshot |

---

## Phase 12: Orchestration

_Scheduled, event-driven and streaming workflows._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| ORC-01 | Scheduled job | SQL incremental + FX daily | 🔄 BUILT, NOT VALIDATED | P0 | BRZ-01 | deployment/jobs.yml (generated): edap-routine-daily (Common landing/bronze/silver/gold, then each asset class bronze->silver->gold) + edap-adhoc; not deployed |
| ORC-02 | File-arrival trigger | Position file arrival starts the pipeline | 🔄 BUILT, NOT VALIDATED | P0 | BRZ-02 | deployment/jobs.yml (generated): edap-positions-on-file-arrival (file_arrival trigger -> landing -> each asset-class bronze + silver position); not deployed |
| ORC-03 | Streaming job | Continuous event ingestion | 🔄 BUILT, NOT VALIDATED | P1 | BRZ-03 | deployment/jobs.yml (generated): edap-trade-events-drain (every 15 min -> landing -> bronze -> silver trade_event per asset class); not deployed |
| ORC-04 | End-to-end workflow | Landing -> Gold with dependencies | 📋 TODO | P0 | GLD-02 | Successful full run |

---

## Phase 13: Monitoring, Audit, Alerting & Cost

_Observability built on the run log and system tables._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| MON-01 | Run/audit log | Pipeline, counts, duration, status | 📋 TODO | P0 | FWK-04 | audit tables populated |
| MON-02 | Ops dashboard | Success/fail, freshness, DQ, quarantine | 📋 TODO | P1 | MON-01 | Dashboard |
| MON-03 | Alerts | Pipeline failure, DQ breach, file missing | 📋 TODO | P1 | MON-01 | Test alert received |
| MON-04 | Cost/usage | System-table usage query; tagging | 📋 TODO | P2 | ORC-04 | Query result |

---

## Phase 14: Governance, Security & Lineage

_Controls demonstrated, not just documented._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| GOV-01 | Ownership, descriptions, tags | UC comments/tags on key objects | 🔄 BUILT, NOT VALIDATED | P1 | FWK-05 | definitions/governance/ownership.yml + governance/apply.py apply_ownership (catalog + 10 schemas) and table tags in loaders; not run |
| GOV-02 | Access control | Personas/groups + grants; one denied-access demo | 🔄 BUILT, NOT VALIDATED | P0 | FWK-05 | definitions/governance/access.yml (4 personas, grants, denied-access demo) + apply_grants; groups must exist at account level; not run |
| GOV-03 | Lineage | End-to-end UC lineage screenshot | 🔄 BUILT, NOT VALIDATED | P0 | GLD-02 | apply.lineage_report (system.access.table_lineage -> edap.monitoring.lineage_paths); screenshot needs a run |
| GOV-04 | Sensitive-column masking | One masked column | 🔄 BUILT, NOT VALIDATED | P2 | GOV-02 | definitions/governance/masking.yml (LEI mask) + apply_masks; not run |

---

## Phase 15: Reconciliation & Testing

_Evidence for Chapters 13-14._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| REC-01 | Record-count reconciliation | Source->Bronze->Silver->Gold with explained differences | 📋 TODO | P0 | GLD-02 | Table with real numbers |
| REC-02 | Attribute-level reconciliation | Sampled attribute comparison | 📋 TODO | P0 | SLV-02 | Table with real numbers |
| REC-03 | Aggregate/business reconciliation | Totals vs expected reference | 📋 TODO | P0 | GLD-03 | Table with real numbers |
| TST-01 | Unit tests | Framework functions | 📋 TODO | P0 | FWK-02 | pytest green |
| TST-02 | Integration + end-to-end | D0 and D1 full runs | 📋 TODO | P0 | ORC-04 | Test report |

---

## Phase 16: Deployment

_Bundles and CI._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| DEP-01 | Declarative Automation Bundle | Jobs/pipelines/dashboards as code | 📋 TODO | P1 | ORC-04 | `bundle deploy` to v2-0 |
| DEP-02 | Environment configs | dev/test/prod overlays | 📋 TODO | P2 | DEP-01 | Overlay switch |
| DEP-03 | CI | Lint + tests on push | 📋 TODO | P2 | FND-09 | CI run |

---

## Phase 17: Dissertation Evidence & Viva Demo

_Turn the build into evidence and a rehearsed demo._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| DOC-01 | Fill TBD tables (Ch. 13-14, App. D/E/G/H) | Replace placeholders with measured results only | 📋 TODO | P0 | REC-01..03 | No TBD left |
| DOC-02 | Screenshots | Per the evidence list in the spec | 📋 TODO | P0 | Phases 1-15 | docs/dissertation_evidence |
| DOC-03 | Report fixes | Employer name, supervisor spelling, dates, missing Appendix F, figures/captions | 📋 TODO | P0 | - | Checklist re-verified |
| DOC-04 | 20-minute demo script | D0 -> D1 -> bad file -> quarantine -> reprocess -> Gold -> dashboard | 🔄 BUILT, NOT VALIDATED | P0 | SRC-04, CON-01 | docs/viva/demo_script.md: timed 20-minute draft; dry run needs the validated pipeline and dashboard |
| DOC-05 | Viva Q&A prep | Defend design choices (YAML, DQX, canonical model) | 🔄 BUILT, NOT VALIDATED | P1 | DOC-04 | docs/viva/viva_qa.md: 12 questions drafted |
