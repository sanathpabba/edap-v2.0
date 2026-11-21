#!/usr/bin/env bash
# Upload the built wheel to a Unity Catalog volume so clusters, notebooks and jobs can install it.
#   tools/publish_wheel.sh [--profile v2] [--volume /Volumes/edap/metadata/artifacts] [wheel-file]
# Needs the volume (deployment/unity_catalog_setup.sql) and an authenticated Databricks CLI profile.
# Credentials: export DATABRICKS_CONFIG_FILE=<project>/.databrickscfg   (the CLI reads profiles from there)
set -euo pipefail
PROFILE="v2"; VOLUME="/Volumes/edap/metadata/artifacts"; WHEEL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2;;
    --volume)  VOLUME="$2"; shift 2;;
    *)         WHEEL="$1"; shift;;
  esac
done
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -n "$WHEEL" ] || WHEEL="$(ls -t "$HERE"/dist/edap_framework-*.whl 2>/dev/null | head -1 || true)"
[ -f "$WHEEL" ] || { echo "no wheel found: run python tools/build_wheel.py first" >&2; exit 1; }
NAME="$(basename "$WHEEL")"
databricks fs cp "$WHEEL" "dbfs:${VOLUME}/${NAME}" --overwrite --profile "$PROFILE"
echo "published: ${VOLUME}/${NAME}"
echo "install in a notebook : %pip install ${VOLUME}/${NAME}[dq]"
echo "install on a cluster  : tools/install_on_cluster.sh --cluster-id <id> --wheel ${VOLUME}/${NAME} --profile ${PROFILE}"
echo "serverless job        : environment dependency  ${VOLUME}/${NAME}"
