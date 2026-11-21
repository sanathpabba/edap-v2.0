# Common tasks. Uses the project virtualenv (.venv); create it with: python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
PY ?= .venv/bin/python

.PHONY: validate test generate wheel publish install-cluster ci

validate:                ## cross-check all definitions and the pipelines tree
	$(PY) runners/validate_definitions.py

test:                    ## offline unit tests
	$(PY) -m pytest tests -q

generate:                ## regenerate pipelines/ and deployment/jobs.yml from the step tables
	$(PY) tools/generate_pipelines.py

wheel:                   ## build dist/edap_framework-<version>+<sha>-py3-none-any.whl
	$(PY) tools/build_wheel.py --version-suffix "$$(git rev-parse --short HEAD)"

publish: wheel           ## upload the wheel to the UC volume (needs DATABRICKS_CONFIG_FILE and a v2 profile)
	tools/publish_wheel.sh --profile v2

install-cluster:         ## make install-cluster CLUSTER=<id> WHEEL=/Volumes/edap/metadata/artifacts/<file>.whl
	tools/install_on_cluster.sh --cluster-id $(CLUSTER) --wheel $(WHEEL) --profile v2

ci: validate test wheel  ## what the CI workflow runs
