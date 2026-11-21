# Pipelines

`pipelines/<AssetClass>/<layer>/<Routine|Adhoc>/NN_<step>.py`

- **Asset classes:** Equities, FixedIncome, FX, Commodities, plus **Common** (landing for every source, instrument master, portfolios, accounts,
  counterparties, FX rates, the conformed FX dimension). Common runs first.
- **Layers:** landing (Common only), bronze, silver, gold.
- **Routine** = the scheduled incremental run. **Adhoc** = on demand: initial load, backfill, replay, rebuild, what-if.
- **Each numbered file calls one framework function** (`edap_framework/pipeline/<layer>_steps.py`); the order of the files is the pipeline.
  A runner executes the steps in order for every item of the layer (tables / entities / products), as listed in `definitions/asset_classes/*.yml`.

```bash
python pipelines/run.py --asset-class Equities --layer bronze --mode Routine
python pipelines/run.py --asset-class Equities --layer silver --mode Adhoc --item trade --from-ts 2026-11-17
python pipelines/run.py --asset-class Equities --layer bronze --mode Routine --steps 1-5 --dry-run      # show the plan
python pipelines/run.py --asset-class ALL --layer silver --mode Routine                                  # Common, then every asset class
```
Regenerate this tree after editing the step tables: `python tools/generate_pipelines.py`.
