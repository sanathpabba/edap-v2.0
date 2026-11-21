# EDAP 2.0 - Project Tracker

**Project**: BITS Pilani MBA Business Analytics Dissertation - modular, YAML-driven framework for Capital Markets reporting modernization  
**Approach**: Phase-wise, **source systems first** (initial + incremental load demo), then the metadata-driven framework  
**Last Updated**: 2026-11-20  

## Ground rules

1. **Evidence before DONE.** A task is only marked ✅ with a command, query output or file that proves it (Evidence column). No percentage claims without measured results.
2. **Everything configurable lives in `definitions/` (YAML).** Framework code in `edap_framework/` has no hard-coded source, table or column names.
3. **Synthetic data only; no secrets in code or notebooks** (Key Vault / secret scope).
4. **One master ID standard** across all sources (FND-05) - the main 1.0 failure to avoid.
5. **DQX** is the DQ engine at Bronze and Silver (not custom SQL, not DLT expectations).
6. Finish and verify each phase before starting the next; 1.0 assets are reused only after they pass verification (♻️ REWORK).

## Status overview

| Phase | Name | Tasks | Done | Rework | Blocked | Todo |
|---|---|---|---|---|---|---|
| 0 | Foundation & Decisions | 12 | 11 | 0 | 0 | 1 |
| 1 | Source 1 - Azure SQL (initial + incremental) | 12 | 0 | 1 | 0 | 11 |
| 2 | Source 2 - Position Files (good + bad) | 7 | 0 | 0 | 0 | 7 |
| 3 | Source 3 - Streaming Trade Events | 7 | 0 | 0 | 0 | 7 |
| 4 | Source 4 - REST FX Rates | 5 | 0 | 0 | 0 | 5 |
| 5 | Source Systems Demo Pack | 6 | 0 | 0 | 0 | 6 |
| 6 | YAML Specification & Framework Core | 6 | 0 | 0 | 0 | 6 |
| 7 | Landing & Bronze (metadata-driven) | 8 | 0 | 0 | 0 | 8 |
| 8 | Data Quality (DQX) - Bronze & Silver | 6 | 0 | 0 | 0 | 6 |
| 9 | Silver - Canonical Model & Reference Data | 6 | 0 | 0 | 0 | 6 |
| 10 | Gold Data Products | 6 | 0 | 0 | 0 | 6 |
| 11 | Consumption | 3 | 0 | 0 | 0 | 3 |
| 12 | Orchestration | 4 | 0 | 0 | 0 | 4 |
| 13 | Monitoring, Audit, Alerting & Cost | 4 | 0 | 0 | 0 | 4 |
| 14 | Governance, Security & Lineage | 4 | 0 | 0 | 0 | 4 |
| 15 | Reconciliation & Testing | 5 | 0 | 0 | 0 | 5 |
| 16 | Deployment | 3 | 0 | 0 | 0 | 3 |
| 17 | Dissertation Evidence & Viva Demo | 5 | 0 | 0 | 0 | 5 |
| | **TOTAL** | **109** | **11** | **1** | **0** | **97** |

**Verified complete: 11/109 tasks.** (Phase 0 verified 2026-11-20; one task is blocked on the user.)

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
| 🔄 IN PROGRESS | Being worked on |
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
| FND-12 | Rotate SQL admin password & Event Hubs root key | Both appeared in plaintext in 1.0 files/chat; rotate and update Key Vault (breaks 1.0 notebooks - acceptable) | 📋 TODO | P1 | FND-07 | New secret versions in Key Vault; old values rejected |
| FND-09 | Git repo for 2.0 | Initialise repo, .gitignore, connect remote, first commit | ✅ DONE | P1 | - | git repo on main, commit c6e6e1a; .gitignore excludes .databrickscfg, config/*.env, chat.json; secret scan clean |
| FND-10 | DQX feasibility | Install databricks-labs-dqx on v2-0 runtime; run one YAML check end-to-end | ✅ DONE | P0 | FND-04 | Serverless job on v2-0: DQX 0.17.2 installs; YAML rules via apply_checks_by_metadata_and_split -> 3 valid / 4 quarantined of 5; is_in_list needs quoted literals or sql_expression; warn rows appear in both outputs |
| FND-11 | Reconcile env files | Single clean env config (region, duplicates, empty KEY_VAULT_URI) | ✅ DONE | P2 | FND-07 | config/azure.env (no secrets, values read from Azure); secrets referenced by Key Vault name; infra/get_secret.sh |

---

## Phase 1: Source 1 - Azure SQL (initial + incremental)

_Repair the SQL source and make initial and incremental loads demonstrable._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| SQL-01 | Schema review vs spec | Compare 1.0 tables with the spec: add trade currency, check watermark columns | ♻️ REWORK | P0 | FND-05 | Gap list + DDL diff |
| SQL-02 | Idempotent DDL scripts | Rewrite/verify create-schema, tables, constraints, indexes; safe to re-run | 📋 TODO | P0 | SQL-01 | Script re-run produces no errors/changes |
| SQL-03 | Reference data redesign | Instruments (type-consistent price/currency/exchange), portfolios, accounts, counterparties on the master ID standard | 📋 TODO | P0 | FND-05 | Row counts + domain checks pass |
| SQL-04 | Account-portfolio consistency | Fix 582 trades whose account belongs to a different portfolio | 📋 TODO | P0 | SQL-03 | Query shows 0 mismatches |
| SQL-05 | Realistic trade lifecycle | Statuses/types follow a believable lifecycle (NEW->EXECUTED->SETTLED; amend/cancel link to an original trade) | 📋 TODO | P0 | SQL-03 | Distribution + lifecycle validation queries |
| SQL-06 | Realistic prices & notionals | Price/quantity depend on instrument type; add trade currency | 📋 TODO | P1 | SQL-03 | Profile query within agreed ranges |
| SQL-07 | Initial load (D0) | Generate ~5,000 trades + reference data from the generator (seeded, reproducible) | 📋 TODO | P0 | SQL-02..06 | Counts + FK integrity + checksums recorded |
| SQL-08 | Incremental scenario (D1) | Generator applies inserts + updates + cancels with new last_updated_ts; known counts | 📋 TODO | P0 | SQL-07 | Expected delta counts documented and verified |
| SQL-09 | Incremental scenario (D2) | Second increment incl. late update to an old trade (late-arriving case) | 📋 TODO | P1 | SQL-08 | Delta verified |
| SQL-10 | Validation script | Repeatable checks: counts, FKs, nulls, domains, arithmetic, watermark coverage | 📋 TODO | P0 | SQL-07 | Script output saved in docs/dissertation_evidence |
| SQL-11 | Generator under source_generators/ | Config-driven (YAML) generator, seed, volumes, scenario switch D0/D1/D2 | 📋 TODO | P1 | SQL-07 | `generate --scenario d1` works |
| SQL-12 | Source README + runbook | How to reset, load D0, apply D1/D2, validate | 📋 TODO | P1 | SQL-10 | Runbook followed from scratch successfully |

---

## Phase 2: Source 2 - Position Files (good + bad)

_Daily position extracts on the master ID standard with deliberate defects._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| FILE-01 | File schema (YAML) | Position CSV schema as a definition file | 📋 TODO | P0 | FND-05 | definitions/sources/positions.yml |
| FILE-02 | Generator from real keys | Generate positions from the actual SQL reference keys (~2,000 rows total) | 📋 TODO | P0 | SQL-07 | Join to reference data = 100% on good files |
| FILE-03 | Good files D0/D1 | positions_YYYYMMDD.csv for initial and next day | 📋 TODO | P0 | FILE-02 | Files + row counts documented |
| FILE-04 | Bad file with all defect types | Missing portfolio, duplicate position_id, invalid quantity, invalid currency, unknown instrument, invalid date | 📋 TODO | P0 | FILE-02 | Each defect type counted in a manifest |
| FILE-05 | ADLS landing structure | landing/positions/{inbound,processed,archive,quarantine} | 📋 TODO | P0 | FND-01 | `az storage fs` listing |
| FILE-06 | Upload scripts | Drop good file / drop bad file into inbound (simulates arrival) | 📋 TODO | P1 | FILE-05 | Both files visible in inbound |
| FILE-07 | README | File source patterns and demo steps | 📋 TODO | P2 | FILE-06 | Doc reviewed |

---

## Phase 3: Source 3 - Streaming Trade Events

_Event Hubs events that tie back to real trades, with lifecycle and defects._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| STR-01 | Event schema (YAML) | Event payload definition (event_id, trade_id, types TRADE_EXECUTED/AMENDED/CANCELLED/SETTLED) | 📋 TODO | P0 | FND-05 | definitions/sources/trade_events.yml |
| STR-02 | Producer from real keys | Events reference real trade/instrument/portfolio IDs; all 9 currencies | 📋 TODO | P0 | SQL-07 | Join to SQL trades >= expected % |
| STR-03 | Lifecycle & edge cases | Duplicates, out-of-order, late-arriving, malformed events (controlled counts) | 📋 TODO | P0 | STR-02 | Manifest of injected anomalies |
| STR-04 | Send burst D0 / D1 | Publish initial burst and a later burst to trade-events hub | 📋 TODO | P0 | STR-03 | Event Hubs IncomingMessages metric = expected |
| STR-05 | Consumer verification | Read back from Event Hubs (Kafka endpoint) to confirm payloads | 📋 TODO | P1 | STR-04 | Sample of consumed events |
| STR-06 | Security | Connection string from Key Vault; Send-only/Listen-only policies | 📋 TODO | P1 | FND-07 | No shared root key in use |
| STR-07 | README | Streaming source runbook | 📋 TODO | P2 | STR-04 | Doc reviewed |

---

## Phase 4: Source 4 - REST FX Rates

_Real FX rates for all instrument/portfolio currencies._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| API-01 | API choice + schema (YAML) | Public no-credential FX API; rate_date, base, quote, rate, source | 📋 TODO | P0 | - | definitions/sources/fx_rates.yml |
| API-02 | Currency coverage | Cover AUD, CAD, CHF, EUR, GBP, HKD, JPY, SGD, USD | 📋 TODO | P0 | API-01 | All pairs returned |
| API-03 | Client with retry/validation | Retry, status check, timestamp, stale-data flag | 📋 TODO | P1 | API-01 | Failure-path test (forced error) |
| API-04 | Capture raw responses | Save JSON responses (landing) for D0 and D1 dates | 📋 TODO | P0 | API-03 | Files in landing/fx_rates |
| API-05 | README | API source notes | 📋 TODO | P2 | API-04 | Doc reviewed |

---

## Phase 5: Source Systems Demo Pack

_Package all four sources into one repeatable initial + incremental demo._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| SRC-01 | Scenario definition | Define D0 (initial), D1, D2 across all four sources with expected counts | 📋 TODO | P0 | Phases 1-4 | docs/runbooks/demo_scenarios.md |
| SRC-02 | One-command reset | Reset all sources to a clean state | 📋 TODO | P0 | SRC-01 | Reset runs clean twice in a row |
| SRC-03 | One-command D0 load | Initial load for SQL, files, events, FX | 📋 TODO | P0 | SRC-02 | Post-load verification report |
| SRC-04 | One-command D1/D2 | Apply incremental changes across sources | 📋 TODO | P0 | SRC-03 | Delta verification report |
| SRC-05 | Cross-source consistency check | IDs join across SQL, files, events, FX currencies | 📋 TODO | P0 | SRC-03 | Report: 100% key resolution (except planned defects) |
| SRC-06 | Source evidence capture | Screenshots/queries for the dissertation (sources chapter) | 📋 TODO | P1 | SRC-04 | Files in docs/dissertation_evidence |

---

## Phase 6: YAML Specification & Framework Core

_Define the YAML contracts and the core of the modular PySpark framework._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| FWK-01 | YAML schemas | Contracts for source, ingestion, mapping, DQ rules, reference data, Gold product, consumption | 📋 TODO | P0 | FND-05, FND-06 | definitions/ examples validate against schema |
| FWK-02 | Config loader + validator | Load/validate YAML, environment overlays, clear errors | 📋 TODO | P0 | FWK-01 | Unit tests |
| FWK-03 | Run context | run_id/batch_id, logging, environment | 📋 TODO | P0 | FWK-02 | Unit tests |
| FWK-04 | Metadata/control tables | Source registry, watermark store, run log (UC tables) | 📋 TODO | P0 | FND-06 | Tables created from YAML |
| FWK-05 | Unity Catalog setup | Catalog, schemas, volumes, external locations via script/bundle | 📋 TODO | P0 | FND-06 | Catalog Explorer screenshot |
| FWK-06 | Packaging | Build wheel, install on cluster, import test | 📋 TODO | P1 | FWK-02 | `import edap_framework` on both workspaces |

---

## Phase 7: Landing & Bronze (metadata-driven)

_Generic ingestion engine driven by YAML for all four sources._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| BRZ-01 | Generic reader - SQL | JDBC read, full + incremental by watermark | 📋 TODO | P0 | FWK-04 | D0 then D1 delta only |
| BRZ-02 | Generic reader - files | Auto Loader / batch on inbound, file registry | 📋 TODO | P0 | FWK-04 | Good + bad file ingested |
| BRZ-03 | Generic reader - streaming | Structured Streaming from Event Hubs, checkpoint | 📋 TODO | P0 | FWK-04 | Events landed with offsets |
| BRZ-04 | Generic reader - REST | API pull to landing then Bronze | 📋 TODO | P1 | FWK-04 | FX rows in Bronze |
| BRZ-05 | Bronze writer + audit columns | Standard _source/_ingestion/_batch/_run/_hash columns | 📋 TODO | P0 | BRZ-01 | Columns present on all Bronze tables |
| BRZ-06 | Schema validation | Expected vs actual schema, drift handling | 📋 TODO | P1 | BRZ-05 | Drift test case |
| BRZ-07 | Idempotency | Re-run does not duplicate | 📋 TODO | P0 | BRZ-05 | Re-run count unchanged |
| BRZ-08 | Onboard a source by YAML only | Add a new table with no code changes | 📋 TODO | P0 | BRZ-01 | Demo of onboarding |

---

## Phase 8: Data Quality (DQX) - Bronze & Silver

_DQX-based declarative checks from YAML with quarantine._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| DQ-01 | DQ wrapper | Framework function reads dq_rules YAML and applies DQX | 📋 TODO | P0 | FND-10, FWK-01 | Unit + integration test |
| DQ-02 | Bronze rules | Technical checks per spec | 📋 TODO | P0 | DQ-01 | Results table populated |
| DQ-03 | Silver rules | Business/referential checks | 📋 TODO | P0 | DQ-01 | Results table populated |
| DQ-04 | Quarantine tables | bronze_invalid, silver_invalid with reasons | 📋 TODO | P0 | DQ-01 | Bad file rows land in quarantine |
| DQ-05 | DQ metrics | Rule-level counts and pass/fail summary | 📋 TODO | P1 | DQ-01 | monitoring.dq_summary |
| DQ-06 | Remediation + reprocess | Fix and reprocess a quarantined file/record | 📋 TODO | P0 | DQ-04 | Before/after evidence |

---

## Phase 9: Silver - Canonical Model & Reference Data

_Seven canonical entities driven by mapping YAML._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| SLV-01 | Mapping engine | Source-to-canonical via YAML (rename, cast, lookup, derive) | 📋 TODO | P0 | FWK-01 | Unit tests |
| SLV-02 | Canonical entities | Trade, Instrument, Portfolio, Position, Counterparty, Account, Market Data | 📋 TODO | P0 | SLV-01, BRZ-05 | 7 tables with contract tests |
| SLV-03 | Reference data | Currency, status, country etc., versioned, effective dates | 📋 TODO | P0 | FWK-05 | Lookups used by Silver |
| SLV-04 | Key resolution & dedup | Business-key handling, duplicate events/files | 📋 TODO | P0 | SLV-02 | Duplicate test case |
| SLV-05 | Late-arriving/updated records | Merge logic for incremental updates | 📋 TODO | P0 | SLV-02, SQL-09 | Late update reflected |
| SLV-06 | Lineage columns | Source references retained in canonical records | 📋 TODO | P1 | SLV-02 | Trace one record end to end |

---

## Phase 10: Gold Data Products

_Four reusable products defined in YAML._

| ID | Task | Description | Status | Priority | Dependencies | Evidence |
|----|------|-------------|--------|----------|--------------|----------|
| GLD-01 | Product builder | Join/measure/aggregate from product YAML | 📋 TODO | P0 | SLV-02 | Unit tests |
| GLD-02 | Trade Analytics | Reusable trade product | 📋 TODO | P0 | GLD-01 | Grain + measures documented |
| GLD-03 | Position & Exposure (with FX) | Market value converted to a common currency | 📋 TODO | P0 | GLD-01, BRZ-04 | Totals reconcile |
| GLD-04 | P&L / Finance | Finance product | 📋 TODO | P1 | GLD-01 | Documented |
| GLD-05 | Regulatory/Management | Controlled reporting product | 📋 TODO | P1 | GLD-01 | Documented |
| GLD-06 | Product documentation | Purpose, grain, owner, consumers, refresh | 📋 TODO | P1 | GLD-02 | Catalog comments set |

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
| ORC-01 | Scheduled job | SQL incremental + FX daily | 📋 TODO | P0 | BRZ-01 | Run history |
| ORC-02 | File-arrival trigger | Position file arrival starts the pipeline | 📋 TODO | P0 | BRZ-02 | Trigger demo |
| ORC-03 | Streaming job | Continuous event ingestion | 📋 TODO | P1 | BRZ-03 | Running stream |
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
| GOV-01 | Ownership, descriptions, tags | UC comments/tags on key objects | 📋 TODO | P1 | FWK-05 | Catalog Explorer |
| GOV-02 | Access control | Personas/groups + grants; one denied-access demo | 📋 TODO | P0 | FWK-05 | Grant + denied query |
| GOV-03 | Lineage | End-to-end UC lineage screenshot | 📋 TODO | P0 | GLD-02 | Screenshot |
| GOV-04 | Sensitive-column masking | One masked column | 📋 TODO | P2 | GOV-02 | Query as restricted user |

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
| DOC-04 | 20-minute demo script | D0 -> D1 -> bad file -> quarantine -> reprocess -> Gold -> dashboard | 📋 TODO | P0 | SRC-04, CON-01 | Dry run timed |
| DOC-05 | Viva Q&A prep | Defend design choices (YAML, DQX, canonical model) | 📋 TODO | P1 | DOC-04 | Notes |
