# Build and deploy: wheel, publish, install, CI

The framework ships as one wheel, **`edap_framework-<version>-py3-none-any.whl`**. It is self-contained: the Python code, **all YAML definitions and
the whole `pipelines/` step tree** are packaged as resources inside it, plus two console commands.

| Command | What it does |
|---|---|
| `edap-run --asset-class Equities --layer bronze --mode Routine [--item ...] [--dry-run]` | runs a pipeline (same as `python pipelines/run.py ...`); this is what the jobs call |
| `edap-validate` | cross-checks every definition and the pipelines tree (works offline) |

Where the code finds its definitions: `$EDAP_PROJECT_ROOT` if set, else the repository checkout, else the copy bundled in the wheel.
So an installed wheel needs no repository, and a developer can still point at a working copy by setting `EDAP_PROJECT_ROOT`.
**Changing a definition means building a new wheel** (the definitions travel inside it).

## 1. Build
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt     # once
make ci                    # validate definitions + unit tests + build the wheel
make wheel                 # just the wheel: dist/edap_framework-0.1.0+<git sha>-py3-none-any.whl
python tools/build_wheel.py                       # release build, version exactly 0.1.0
python tools/build_wheel.py --version-suffix x1   # version 0.1.0+x1
```
The build runs in a temporary staging copy (the repository stays clean) and then **verifies the wheel**: every file under `definitions/` and `pipelines/`
must be inside it and both console commands must exist; otherwise the build fails. Version lives in one place: `edap_framework/__init__.py`.
Local builds add the git sha (`0.1.0+abc1234`) so every build has a unique version: a cluster never silently keeps an older wheel with the same version.

## 2. Publish to Databricks
One-time: create the volume (it is in `deployment/unity_catalog_setup.sql`): `CREATE VOLUME IF NOT EXISTS edap.metadata.artifacts`.
```bash
export DATABRICKS_CONFIG_FILE=$PWD/.databrickscfg          # the CLI profiles (v2 = the 2.0 workspace)
make publish                                               # builds, then uploads to /Volumes/edap/metadata/artifacts/
# or:  tools/publish_wheel.sh --profile v2 --volume /Volumes/edap/metadata/artifacts dist/edap_framework-....whl
```

## 3. Install, by compute type
| Where | How |
|---|---|
| **Serverless jobs** (the generated jobs) | automatic: `databricks bundle deploy` builds the wheel (`artifacts` in `databricks.yml`) and the job environment installs `../dist/*.whl` plus `databricks-labs-dqx==0.17.2`; tasks are `python_wheel_task` -> `edap-run` |
| **Notebook** (serverless or classic) | `%pip install /Volumes/edap/metadata/artifacts/<wheel>.whl[dq]` then `dbutils.library.restartPython()` |
| **Classic / all-purpose cluster** | `make install-cluster CLUSTER=<cluster-id> WHEEL=/Volumes/edap/metadata/artifacts/<wheel>.whl` (cluster library; add `--uninstall-old` and restart when replacing a wheel of the same version) |

Smoke test after any install (notebook cell or job):
```python
import edap_framework; print(edap_framework.__version__)
!edap-validate        # 0 error(s) expected
```

## 4. CI (GitHub Actions, `.github/workflows/`)
- **ci.yml** (every push to `main` and every pull request; Python 3.9 and 3.11): validate definitions -> check the generated `pipelines/` and `deployment/jobs.yml` are up to date
  -> unit tests -> build the wheel -> install it in a clean virtualenv and run `edap-validate` and an `edap-run --dry-run` from outside the repository -> upload the wheel as an artifact.
- **release.yml**: push a tag `vX.Y.Z` (must equal `edap_framework.__version__`) -> tests -> wheel attached to a GitHub release.
  Run it manually (`workflow_dispatch`, `deploy_target` = dev/test/prod) to also `databricks bundle validate` and `deploy` that target.
  Deploy needs GitHub secrets `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET` (an OAuth service principal) and a GitHub environment named `databricks-<target>`
  with required reviewers. No credentials are ever stored in the repository, and `databricks.yml` excludes `.databrickscfg*`, `chat.json`, `config/*.env` from syncing.

## 5. Release steps
1. Change `__version__` in `edap_framework/__init__.py`, commit, push (CI must be green).
2. `git tag v0.2.0 && git push origin v0.2.0` -> release workflow builds and attaches the wheel.
3. Deploy: run the release workflow manually for the target, or locally `databricks bundle deploy -t dev --profile v2`.

## Not yet verified
Built and installed in a clean virtualenv (outside the repository, no Spark) with `edap-validate` and `edap-run --dry-run` passing; 75 offline tests including that build.
Not yet done: GitHub Actions run, upload to the UC volume, cluster/serverless installation, `bundle validate/deploy` on the v2-0 workspace, running a pipeline on Databricks.
Python 3.11 (serverless environment 2) is covered by the CI matrix, not run locally.
