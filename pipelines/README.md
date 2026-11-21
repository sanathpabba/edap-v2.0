# Pipelines

`pipelines/<AssetClass>/<layer>/<table>/<Routine|Adhoc>/NN_<step>.py`

- **One folder per table** (bronze/landing: `sql_trades`, `file_positions` ...; silver: entity; gold: data product), so an asset class can hold
  hundreds of tables and each keeps its own step files. The tables of a layer are listed, in run order, in `definitions/asset_classes/*.yml`.

- **Asset classes:** Equities, FixedIncome, FX, Commodities, plus **Common** (landing for every source, instrument master, portfolios, accounts,
  counterparties, FX rates, the conformed FX dimension). Common runs first.
- **Layers:** landing (Common only), bronze, silver, gold.
- **Routine** = the scheduled incremental run. **Adhoc** = on demand: initial load, backfill, replay, rebuild, what-if.
- **Each numbered file calls one framework function** (`edap_framework/pipeline/<layer>_steps.py`); the order of the files is the pipeline.
  The runner executes each table's steps in order, table after table.

```bash
python pipelines/run.py --asset-class Equities --layer bronze --mode Routine
python pipelines/run.py --asset-class Equities --layer silver --mode Adhoc --item trade --from-ts 2026-11-17     # one table
python pipelines/run.py --asset-class Equities --layer bronze --mode Routine --steps 1-5 --dry-run      # show the plan
python pipelines/run.py --asset-class ALL --layer silver --mode Routine                                  # Common, then every asset class
```
Regenerate this tree after editing the step tables: `python tools/generate_pipelines.py`.
