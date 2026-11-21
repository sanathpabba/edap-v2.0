# Onboard a new SQL table (YAML only, no code change)

1. Add the table to `definitions/sources/azure_sql_trading.yml` under `objects:` (name, business_key, load_type, watermark_column, columns).
   Quote types that contain a comma: `qty: "decimal(18,4)"` (an unquoted comma splits the YAML entry; the validator rejects it).
2. Generate the specs: `python runners/scaffold_sql_table.py --object schema.table`
   -> `definitions/landing/sql-loads/<t>.yml`, `definitions/bronze/sql-loads/<t>.yml`, starter `definitions/dq_rules/bronze/sql_<t>.yml`.
3. Extend the DQ rules if needed (formats, domains), then `python runners/validate_definitions.py`.
4. Add the item (`sql-loads/<t>`) to `landing` and `bronze` in `definitions/asset_classes/common.yml` (shared table) or to an asset class `bronze` list (routed by instrument),
   then run `python pipelines/run.py --asset-class Common --layer landing --item sql-loads/<t>`, then `--layer bronze` (it runs DQX at the end).
5. To carry it to Silver, add `definitions/mappings/<entity>.yml` (columns, lookups, dedup, merge, DQ rules); Gold products pick it up through their YAML joins.

Other source types follow the same pattern with their own folder (`file-loads`, `stream-loads`, `api-loads`); copy the closest spec and edit.
