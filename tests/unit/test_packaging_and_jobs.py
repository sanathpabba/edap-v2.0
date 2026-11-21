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
        spec = job["environments"][0]["spec"]
        assert spec["environment_version"] == "4", name                          # the version verified on serverless
        assert "${var.wheel_path}" in spec["dependencies"] and any(d.startswith("databricks-labs-dqx") for d in spec["dependencies"]), name
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


def test_bundle_uses_the_published_wheel_and_syncs_almost_nothing():
    b = yaml.safe_load(open(os.path.join(ROOT, "databricks.yml")))
    default = b["variables"]["wheel_path"]["default"]
    assert default.startswith("/Volumes/edap/metadata/artifacts/edap_framework-") and default.endswith("-py3-none-any.whl")
    assert "artifacts" not in b                                                    # the wheel is built and published by CI, not by the bundle
    assert b["sync"]["paths"] == ["deployment"]                                    # the wheel carries code, definitions and pipelines


def test_ci_and_release_workflows_are_valid_yaml_with_expected_steps():
    ci = open(os.path.join(ROOT, ".github", "workflows", "ci.yml")).read()
    for needle in ("validate_definitions.py", "pytest", "build_wheel.py", "edap-validate", "upload-artifact"):
        assert needle in ci
    rel = yaml.safe_load(open(os.path.join(ROOT, ".github", "workflows", "release.yml")))
    pub = rel["jobs"]["publish"]
    assert pub["environment"].startswith("databricks-") and "DATABRICKS_CLIENT_SECRET" in pub["env"]
    text = open(os.path.join(ROOT, ".github", "workflows", "release.yml")).read()
    assert "databricks fs cp" in text and "/Volumes/edap/metadata/artifacts" in text and "download-artifact" in text
    triggers = rel.get("on") or rel.get(True)                                      # YAML 1.1 reads the key `on` as the boolean True
    assert triggers["workflow_dispatch"]["inputs"]["deploy_jobs"]["default"] is False      # deploying the jobs is opt-in
    assert "bundle deploy" in text and "deploy_jobs == 'true'" in text
