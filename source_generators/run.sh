#!/usr/bin/env bash
# Usage: source_generators/run.sh <python module or script args>   e.g.  run.sh -m azure_sql.generate d0
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export DYLD_LIBRARY_PATH="${DYLD_LIBRARY_PATH:-/opt/homebrew/opt/openssl@3/lib}"
export PYTHONPATH="$HERE"
export PYTHONWARNINGS=ignore
cd "$HERE"
exec "$HERE/../.venv/bin/python" "$@"
