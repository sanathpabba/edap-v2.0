#!/usr/bin/env bash
# Usage: infra/get_secret.sh <secret-name>   (prints the value; requires `az login`)
set -euo pipefail
az keyvault secret show --vault-name edap-kv-b777d5 --name "$1" --query value -o tsv
