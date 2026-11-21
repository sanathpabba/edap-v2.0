import os
import re

import yaml

from edap_framework import __version__
from edap_framework.cli import parse_args, pipelines_for
from edap_framework.core import config

ROOT = config.project_root()


def _jobs():
    return yaml.safe_load(open(os.path.join(ROOT, "deployment", "jobs.yml")))["resources"]["jobs"]


def test_version_and_pyproject_agree():
    text = open(os.path.join(ROOT, "pyproject.toml")).read()
    assert re.match(r"^\d+\.\d+\.\d+$", __version__)
    assert 'version = { attr = "edap_framework.__version__" }' in text
    assert 'edap-run = "edap_framework.cli:main"' in text and 'edap-validate = "edap_framework.core.validator:main"' in text


def test_project_root_prefers_env_then_repo(monkeypatch):
    monkeypatch.setenv("EDAP_PROJECT_ROOT", "/somewhere/else")
    assert config._resolve_root() == "/somewhere/else"
    monkeypatch.delenv("EDAP_PROJECT_ROOT")
    assert os.path.isdir(os.path.join(config._resolve_root(), "definitions"))


def test_every_job_task_runs_the_wheel_and_is_a_valid_edap_run_command():
    placeholders = {"{{job.run_id}}": "123", "{{job.parameters.asset_class}}": "Equities", "{{job.parameters.layer}}": "bronze", "{{job.parameters.extra}}": "date=2026-11-18"}
    for name, job in _jobs().items():
        deps = job["environments"][0]["spec"]["dependencies"]
        assert "../dist/*.whl" in deps and any(d.startswith("databricks-labs-dqx") for d in deps), name
        for t in job["tasks"]:
            w = t["python_wheel_task"]
            assert w["package_name"] == "edap_framework" and w["entry_point"] == "edap-run" and t["environment_key"] == "edap_env"
            args = parse_args([placeholders.get(p, p) for p in w["parameters"]])
            targets = pipelines_for(args.asset_class, args.layer)
            assert targets, (name, t["task_key"])                              # asset class and layer exist
            for item in args.item or []:                                        # --item must name a real table of that pipeline
                assert any(item in a.items[args.layer] or item in [config.table_folder(args.layer, i) for i in a.items[args.layer]] for a in targets), (name, item)


def test_task_dependencies_refer_to_tasks_in_the_same_job():
    for name, job in _jobs().items():
        keys = {t["task_key"] for t in job["tasks"]}
        for t in job["tasks"]:
            assert {d["task_key"] for d in t.get("depends_on", [])} <= keys, (name, t["task_key"])


def test_bundle_builds_the_wheel_and_never_syncs_credentials():
    b = yaml.safe_load(open(os.path.join(ROOT, "databricks.yml")))
    assert b["artifacts"]["edap_framework"]["type"] == "whl" and "tools/build_wheel.py" in b["artifacts"]["edap_framework"]["build"]
    for must in (".databrickscfg*", "chat.json", "config/*.env", ".venv/**"):
        assert must in b["sync"]["exclude"]


def test_ci_and_release_workflows_are_valid_yaml_with_expected_steps():
    ci = open(os.path.join(ROOT, ".github", "workflows", "ci.yml")).read()
    for needle in ("validate_definitions.py", "pytest", "build_wheel.py", "edap-validate", "upload-artifact"):
        assert needle in ci
    rel = yaml.safe_load(open(os.path.join(ROOT, ".github", "workflows", "release.yml")))
    assert "deploy" in rel["jobs"] and rel["jobs"]["deploy"]["environment"].startswith("databricks-")
    assert "DATABRICKS_CLIENT_SECRET" in rel["jobs"]["deploy"]["env"]
