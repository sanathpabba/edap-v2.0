#!/usr/bin/env bash
# Rotate EDAP credentials and store the new values in Key Vault as new secret versions.
# Usage: infra/rotate_secrets.sh sql|eventhub|all      (requires `az login`)
# Secrets are never printed. Consumers read them from Key Vault / the Databricks scope 'edap-kv'.
set -euo pipefail
export DYLD_LIBRARY_PATH="${DYLD_LIBRARY_PATH:-/opt/homebrew/opt/openssl@3/lib}"
RG=edap-rg; KV=edap-kv-b777d5
SQL_SERVER=$(az keyvault secret show --vault-name $KV --name sql-server-name --query value -o tsv)
SQL_DB=$(az keyvault secret show --vault-name $KV --name sql-database-name --query value -o tsv)
SQL_USER=$(az keyvault secret show --vault-name $KV --name sql-admin-user --query value -o tsv)
EH_NS=$(az keyvault secret show --vault-name $KV --name eventhub-namespace --query value -o tsv)
STAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

sql_login_ok() { sqlcmd -S "$SQL_SERVER.database.windows.net" -d "$SQL_DB" -U "$SQL_USER" -P "$1" -C -l 15 -Q "SELECT 1" >/dev/null 2>&1; }

rotate_sql() {
  local old new
  old=$(az keyvault secret show --vault-name $KV --name sql-admin-password --query value -o tsv)
  new="Ed$(openssl rand -hex 12)Ap9X"
  az sql server update -g $RG -n "$SQL_SERVER" --admin-password "$new" >/dev/null
  az keyvault secret set --vault-name $KV --name sql-admin-password --value "$new" --tags rotated=$STAMP >/dev/null
  sleep 20
  sql_login_ok "$new" && echo "sql: NEW password works" || { echo "sql: NEW password FAILED"; exit 1; }
  sql_login_ok "$old" && echo "sql: WARNING old password still works" || echo "sql: OLD password rejected"
}

rotate_eventhub() {
  local conn
  for k in PrimaryKey SecondaryKey; do
    az eventhubs namespace authorization-rule keys renew -g $RG --namespace-name "$EH_NS" --name RootManageSharedAccessKey --key $k >/dev/null
  done
  conn=$(az eventhubs namespace authorization-rule keys list -g $RG --namespace-name "$EH_NS" --name RootManageSharedAccessKey --query primaryConnectionString -o tsv)
  az keyvault secret set --vault-name $KV --name eventhub-connection-string-root --value "$conn" --tags rotated=$STAMP >/dev/null
  echo "eventhub: both root keys renewed; Key Vault updated"
}

case "${1:-}" in
  sql) rotate_sql ;;
  eventhub) rotate_eventhub ;;
  all) rotate_sql; rotate_eventhub ;;
  *) echo "usage: $0 sql|eventhub|all"; exit 2 ;;
esac
