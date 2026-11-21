#!/usr/bin/env bash
# Install a published wheel on an existing (classic / all-purpose) cluster as a cluster library, then show its status.
#   tools/install_on_cluster.sh --cluster-id <id> --wheel /Volumes/edap/metadata/artifacts/edap_framework-0.1.0-py3-none-any.whl [--profile v2] [--uninstall-old]
# Serverless jobs and notebooks do not use cluster libraries: use the job environment dependency or `%pip install <wheel>` (see docs/runbooks/build_and_deploy.md).
set -euo pipefail
PROFILE="v2"; CLUSTER=""; WHEEL=""; OLD=0
while [ $# -gt 0 ]; do
  case "$1" in
    --cluster-id) CLUSTER="$2"; shift 2;;
    --wheel)      WHEEL="$2"; shift 2;;
    --profile)    PROFILE="$2"; shift 2;;
    --uninstall-old) OLD=1; shift;;
    *) echo "unknown argument $1" >&2; exit 1;;
  esac
done
[ -n "$CLUSTER" ] && [ -n "$WHEEL" ] || { echo "usage: $0 --cluster-id <id> --wheel <volume path> [--profile v2]" >&2; exit 1; }
if [ "$OLD" = 1 ]; then   # a new wheel with the same version is only picked up after the old one is removed and the cluster restarted
  databricks libraries uninstall --json "{\"cluster_id\": \"$CLUSTER\", \"libraries\": [{\"whl\": \"$WHEEL\"}]}" --profile "$PROFILE" || true
fi
databricks libraries install --json "{\"cluster_id\": \"$CLUSTER\", \"libraries\": [{\"whl\": \"$WHEEL\"}, {\"pypi\": {\"package\": \"databricks-labs-dqx==0.17.2\"}}]}" --profile "$PROFILE"
databricks libraries cluster-status "$CLUSTER" --profile "$PROFILE"
echo "installed. Smoke test (notebook or job):  import edap_framework; print(edap_framework.__version__)   |   edap-validate"
