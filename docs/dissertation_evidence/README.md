# Dissertation evidence index

Every number in the dissertation should trace to a file here (or to a table once the pipeline has run).

| Evidence | File | What it shows |
|---|---|---|
| SQL source validation, initial load | `sql_validation_d0.md` | 22/22 checks on the initial load (IDs, arithmetic, lifecycle, prices) |
| SQL source validation, increment 1 | `sql_validation_d1.md` | 23/23 checks incl. watermark delta |
| SQL source validation, increment 2 | `sql_validation_d2.md` | 25/25 checks incl. late corrections and outbox consistency |
| Position file validation | `position_files_validation.md` | 4 files; the independently detected defects equal the injected ones (10/6/8/7/5/5) |
| Cross-source verification | `cross_source_verification.md` | 8/8: Event Hubs count equals producer count, keys resolve to SQL, FX covers all currencies |
| Run manifests | `source_manifests/*.json` | Exact counts per scenario (inserts, updates, duplicates, out-of-order, malformed, defects, FX days) |
| Architecture decisions | `../architecture/decisions.md` | Master ID format, catalog/layer naming, DQX placement, config-over-code |
| Design notes | `../architecture/landing_bronze.md`, `../architecture/silver_dq_gold_governance.md` | How each layer is built |

## Still to capture (tracker SRC-06 / DOC-02)
Screenshots after the first Databricks run: Catalog Explorer (tables, tags, comments), UC lineage graph for one Gold product, quarantine
table with the bad position file, `monitoring.dq_summary`, job run history, the denied-access query, the masked LEI column.
