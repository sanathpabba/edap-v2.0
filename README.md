# EDAP 2.0 - Enterprise Data Analytical Platform

A modular, **YAML-driven PySpark framework** that migrates a capital-markets institution from transactional to analytical reporting:
Landing -> Bronze -> Silver (canonical entities) -> Gold (reusable data products) -> Consumption, with DQX data quality, governance,
lineage and reconciliation. All data is synthetic. Built for a BITS Pilani MBA dissertation.

Principle: **everything configurable lives in `definitions/` (YAML); `edap_framework/` has no source-, table- or column-specific code.**

## Layout
| Path | What |
|---|---|
| `definitions/` | sources, landing/bronze specs per source, mappings (Silver), DQ rules, reference data, Gold products, governance, environments |
| `edap_framework/` | generic engines and the step functions: `pipeline/` (context, sequence, `<layer>_steps.py`), ingestion, bronze, silver, dq (DQX), gold, governance, core |
| `pipelines/` | the pipelines: `<AssetClass>/<layer>/<table>/<Routine\|Adhoc>/NN_<step>.py` - every numbered file calls one framework function; `run.py` executes them in order |
| `runners/` | utilities: definition validator, SQL-table scaffold, reference-data and governance runners |
| `source_generators/` | synthetic source systems (Azure SQL, position files, Event Hubs events, FX REST API) with D0/D1/D2 demo scenarios |
| `deployment/` | Unity Catalog setup SQL, generated Databricks job definitions (wheel-based) |
| `tools/` | pipeline-tree generator, wheel build, publish-to-Databricks and install-on-cluster scripts |
| `.github/workflows/` | CI (validate, test, build wheel) and release/deploy |
| `docs/` | architecture decisions, runbooks, dissertation evidence, viva material |
| `tests/` | unit tests (run offline) |
| `PROJECT_TRACKER.md` | phase-wise tracker with evidence per task |

## Package, install and deploy
`make ci` validates, tests and builds `dist/edap_framework-<version>-py3-none-any.whl` (code + definitions + pipelines, console commands `edap-run` and `edap-validate`).
`make publish` uploads it to a Unity Catalog volume; jobs install it as a `python_wheel_task`. See `docs/runbooks/build_and_deploy.md`.

## Run order
`source_generators` (D0/D1/D2) -> `pipelines/run.py --asset-class ALL` for `landing` (Common), `bronze`, `silver`, `gold` -> `runners/governance_apply.py`

## Quick checks (no Databricks needed)
```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python runners/validate_definitions.py     # cross-checks all YAML against each other
.venv/bin/python -m pytest tests -q
```

## Onboard a new SQL table
Add it to `definitions/sources/azure_sql_trading.yml`, then `python runners/scaffold_sql_table.py --object schema.table`
(see `docs/runbooks/onboard_new_source_table.md`).

## Status
See `PROJECT_TRACKER.md`. Sources are built and verified; Landing, Bronze, Silver, DQ, Gold and governance are written and
offline-checked but not yet run on Databricks. Secrets are only in Azure Key Vault (`docs/runbooks/secret_rotation.md`).
