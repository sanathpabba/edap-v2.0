# Architecture Decisions (Phase 0)

Decided 2026-11-20. Changes require updating this file and the tracker.

## D1 - Master ID standard (FND-05)
The Azure SQL source is the system of record. Its ID formats are the master standard for **all** sources
(files, events, FX-related reference joins):

| Entity | Format | Example |
|---|---|---|
| Instrument | `INST` + 5 digits | `INST00080` |
| Portfolio | `PORT` + 4 digits | `PORT0016` |
| Counterparty | `CPTY` + 4 digits | `CPTY0021` |
| Account | `ACC` + 5 digits | `ACC00009` |
| Trade | `TRD` + 7 digits | `TRD0000001` |
| Position | `POS-YYYYMMDD-NNNN` (file source) | `POS-20261120-0001` |
| Event | `EVT` + 8 digits | `EVT00100023` |

Generators for files, events and FX must read keys from the SQL reference tables, never invent their own.
1.0 generators used `INST-045` / `PORT-007` / `ACC-029` and `TRD-STREAM-xxxxxx`; those are retired.

## D2 - Catalog and schemas (FND-06)
- Catalog: **`edap`** (new). 1.0 catalogs (`edap_prod`, `edap_databricks_workspace`) are read-only references and must not be modified.
- Both workspaces share one metastore (`metastore_azure_centralus`), so objects are visible from both.
- Schemas: `landing`, `bronze`, `silver`, `gold`, `consumption`, `metadata`, `reference`, `quarantine`, `monitoring`, `audit`.
- Top layer is **Consumption** (follows the dissertation report), not Platinum.

## D3 - Data quality engine
Databricks Labs **DQX** at Bronze and Silver, rules defined in YAML (`definitions/dq_rules/`).
Not custom SQL, not DLT expectations.

## D4 - Configuration over code
All source, mapping, DQ, reference-data, Gold-product and consumption behaviour is defined in YAML under
`definitions/`. `edap_framework/` contains reusable PySpark functions with no hard-coded source/table/column names.

## D5 - Secrets
No credentials in code, notebooks, YAML or git. Runtime secrets come from Azure Key Vault / a Databricks secret scope.
Local developer credentials live only in git-ignored files (`.databrickscfg`, `config/*.env`).

## D6 - Workspaces
- `edap-databricks-workspace` (v1): serverless-only; retained for the 1.0 reference work.
- `edap-databricks-workspace-v2-0`: Hybrid/Premium, used for 2.0 (serverless + classic compute). CLI profile `v2`.
