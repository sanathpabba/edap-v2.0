# Jobs per asset class and the master runner

## What runs where
| Job | Stages (tasks, in order) | Notes |
|---|---|---|
| `edap-common` | landing -> bronze -> silver -> gold | all landing, instrument master, portfolios, accounts, counterparties, FX rates, the FX dimension. Must run first |
| `edap-equities`, `edap-fixedincome`, `edap-fx`, `edap-commodities` | bronze -> silver -> gold -> **consumption** | each asset class on its own; consumption = metric views + materialized views over its Gold products |
| `edap-master` | `common`, then the four asset-class jobs in parallel | run-job tasks; every job parameter is passed through; schedule paused |
| `edap-positions-on-file-arrival`, `edap-trade-events-drain` | landing + the asset-class bronze/silver for positions / events | event-driven and 15-minute drain variants |
| `edap-adhoc` | one pipeline, one layer | initial load, backfill, replay, rebuild |

Every pipeline job has the same parameters: `mode` (Routine | Adhoc), `stages` (comma list), `date`, `expect_file`, `extra`.
A stage task whose layer is not in `stages` does nothing, so one job can run any subset of its stages.

## Consumption stage (per asset class, 4 objects each = 16)
| Object | Kind | Over |
|---|---|---|
| `<ac>_trade_metrics` | metric view | `<ac>_trade_analytics`: Trade Count, Gross/Net Notional USD, Costs USD, Cost Rate Bps, Failed Trades, Failure Rate, ... by date, side, portfolio, counterparty, rating, strategy |
| `<ac>_exposure_metrics` | metric view | `<ac>_position_exposure`: Market Value, Cost Basis, Unrealized PnL, Gross/Long/Short Exposure by date, portfolio, region, instrument, side |
| `<ac>_trade_daily_mv` | materialized view | daily trade summary per portfolio, side, status |
| `<ac>_portfolio_exposure_mv` | materialized view | daily exposure per portfolio and asset class |
Definitions: `definitions/consumption/*.yml`. Materialized views are created on the first run and refreshed afterwards (`rebuild=true` recreates them).
Statements run on the job's own compute; set `consumption.sql_warehouse_id` in `definitions/environments/dev.yml` to run them on a SQL warehouse instead.

## The master_runner notebook (`deployment/notebooks/master_runner.py`)
Widgets: `asset_classes` (ALL or a list), `stages`, `mode`, `run_date`, `expect_file`, `from_ts`, `to_ts`, `fx_mode`, `rescan`, `rebuild`, `notify`, `extra`, `dry_run`, `wait`.
It installs the newest published wheel, plans the order (Common first, then the asset classes in parallel), triggers the jobs with your parameters, waits, prints a result table,
and **fails the notebook if any run fails** (asset classes are not started when Common fails). The same logic is the console command `edap-master`.

| I want to... | asset_classes | stages | mode | run_date | other |
|---|---|---|---|---|---|
| daily run of everything | ALL | (all) | Routine | (today) | |
| demo day D1 | ALL | (all) | Routine | 2026-11-17 | expects the file for 2026-11-16 |
| only rebuild Gold + consumption for FX | FX | gold,consumption | Routine | | `rebuild`=true to recreate materialized views |
| check the plan, trigger nothing | ALL | | | | `dry_run`=true |
| replay Bronze for Equities from a time | Equities | bronze | Adhoc | | `from_ts`=2026-11-17T00:00:00 |
| initial FX history | Common | landing | Adhoc | 2026-11-17 | `fx_mode`=history |

Command line (needs Databricks authentication): `edap-master --asset-classes ALL --mode Routine --date 2026-11-17 --dry-run`.
In development mode the bundle prefixes job names (`[dev user] edap-equities`); the runner matches on the name's ending.

## Deploying it
Publish the wheel and deploy the jobs: release workflow, `deploy_target=dev`, tick `deploy_jobs` (see build_and_deploy.md). The notebook is synced with the bundle
(`deployment/notebooks/`); import it to your own folder to run it as yourself.

## Not yet verified on Databricks
The per-pipeline jobs, the master job and the notebook are validated offline (bundle validate OK, 103 unit tests including a fake jobs API). The consumption stage's
metric views and materialized views have not been created yet: that needs the Gold products to exist first, and it depends on what your workspace allows.
