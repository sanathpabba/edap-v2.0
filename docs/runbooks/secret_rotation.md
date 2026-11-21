# Secret management & rotation

## Where secrets live
| Secret (Key Vault `edap-kv-b777d5`) | Used for |
|---|---|
| `sql-admin-password`, `sql-admin-user`, `sql-server-name`, `sql-database-name` | Azure SQL source |
| `eventhub-connection-string-root`, `eventhub-namespace`, `eventhub-name` | Event Hubs source (root key; replaced by scoped send/listen policies in STR-06) |
| `storage-account-name` | ADLS |

- Notebooks/jobs read them via the Databricks scope **`edap-kv`** (Azure-backed): `dbutils.secrets.get("edap-kv", "<name>")`.
- Local scripts read them with `infra/get_secret.sh <name>`.
- Never put values in code, YAML, notebooks, docs or git. YAML references secrets **by name** only.

## Rotating
```bash
infra/rotate_secrets.sh sql        # new SQL admin password -> Key Vault (new version), verifies new works and old is rejected
infra/rotate_secrets.sh eventhub   # renews both root keys -> Key Vault
infra/rotate_secrets.sh all
```
Each run adds a new Key Vault secret version tagged `rotated=<UTC time>`. Consumers always read the latest version, so no code change is needed.

## Rotation log
| Date (UTC) | Secret | Reason |
|---|---|---|
| 2026-11-20 | sql-admin-password, eventhub root keys | Previous values appeared in plaintext in 1.0 files and chat history |

## Known impact
1.0 notebooks that hard-coded the old SQL password no longer connect. 2.0 does not use them.
