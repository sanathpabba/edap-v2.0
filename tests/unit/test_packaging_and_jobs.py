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


PLACEHOLDERS = {"{{job.run_id}}": "123", "{{job.parameters.asset_class}}": "Equities", "{{job.parameters.layer}}": "bronze", "{{job.parameters.extra}}": "date=2026-11-18",
                "{{job.parameters.date}}": "2026-11-17", "{{job.parameters.mode}}": "Routine", "{{job.parameters.stages}}": "bronze,silver,gold,consumption",
                "{{job.parameters.expect_file}}": "true"}


def _fill(p):
    for k, v in PLACEHOLDERS.items():
        p = p.replace(k, v)
    return p


def test_every_job_task_runs_the_wheel_and_is_a_valid_edap_run_command():
    for name, job in _jobs().items():
        if name == "edap_master":
            continue                                                                  # run_job tasks only, checked below
        spec = job["environments"][0]["spec"]
        assert spec["environment_version"] == "4", name                          # the version verified on serverless
        assert "${var.wheel_path}" in spec["dependencies"] and any(d.startswith("databricks-labs-dqx") for d in spec["dependencies"]), name
        for t in job["tasks"]:
            w = t["python_wheel_task"]
            assert w["package_name"] == "edap_framework" and w["entry_point"] == "edap-run" and t["environment_key"] == "edap_env"
            args = parse_args([_fill(p) for p in w["parameters"]])
            targets = pipelines_for(args.asset_class, args.layer)
            assert targets, (name, t["task_key"])                              # asset class and layer exist
            for item in args.item or []:                                        # --item must name a real table of that pipeline
                assert any(item in a.items[args.layer] or item in [config.table_folder(args.layer, i) for i in a.items[args.layer]] for a in targets), (name, item)


def test_task_dependencies_refer_to_tasks_in_the_same_job():
    for name, job in _jobs().items():
        keys = {t["task_key"] for t in job["tasks"]}
        for t in job["tasks"]:
            assert {d["task_key"] for d in t.get("depends_on", [])} <= keys, (name, t["task_key"])


def test_one_job_per_pipeline_with_its_stages_in_order():
    from edap_framework import master
    jobs = _jobs()
    for ac in config.list_asset_classes():
        job = jobs["edap_" + ac.folder.lower()]
        assert job["name"] == master.job_name(ac)                                  # the master runner finds the job by this name
        stages = [layer for layer in master.STAGES if layer in ac.items]
        assert [t["task_key"] for t in job["tasks"]] == ["%s_%s" % (ac.folder.lower(), layer) for layer in stages]
        for prev, t in zip(job["tasks"], job["tasks"][1:]):                        # each stage waits for the previous one
            assert t["depends_on"] == [{"task_key": prev["task_key"]}]
        assert {p["name"]: p["default"] for p in job["parameters"]} == {"mode": "Routine", "stages": ",".join(master.STAGES), "date": "", "expect_file": "true", "extra": ""}
    assert [t["task_key"] for t in jobs["edap_common"]["tasks"]][0] == "common_landing"
    assert not any(t["task_key"].endswith("consumption") for t in jobs["edap_common"]["tasks"])          # Common has no consumption stage
    assert [t["task_key"] for t in jobs["edap_equities"]["tasks"]] == ["equities_bronze", "equities_silver", "equities_gold", "equities_consumption"]


def test_stage_tasks_pass_the_job_parameters_to_edap_run():
    job = _jobs()["edap_equities"]
    for t in job["tasks"]:
        a = parse_args([_fill(p) for p in t["python_wheel_task"]["parameters"]])
        assert a.asset_class == "Equities" and a.mode == "Routine" and a.stages == "bronze,silver,gold,consumption" and a.layer == t["task_key"].split("_", 1)[1]
        assert "date=2026-11-17" in a.extra
    landing = next(t for t in _jobs()["edap_common"]["tasks"] if t["task_key"] == "common_landing")["python_wheel_task"]["parameters"]
    assert "expect_file={{job.parameters.expect_file}} date={{job.parameters.date}} {{job.parameters.extra}}" in landing


def test_master_job_runs_common_first_then_every_asset_class_and_passes_all_parameters():
    jobs = _jobs()
    master_job = jobs["edap_master"]
    tasks = {t["task_key"]: t for t in master_job["tasks"]}
    assert "depends_on" not in tasks["common"] and set(tasks) == {"common", "commodities", "equities", "fx", "fixedincome"}
    pass_through = {p["name"]: "{{job.parameters.%s}}" % p["name"] for p in master_job["parameters"]}
    for key, t in tasks.items():
        assert t["run_job_task"]["job_parameters"] == pass_through
        ref = re.match(r"^\$\{resources\.jobs\.(\w+)\.id\}$", t["run_job_task"]["job_id"]).group(1)
        assert ref in jobs, ref
        if key != "common":
            assert t.get("depends_on") == [{"task_key": "common"}] and ref == "edap_" + key
    assert master_job["schedule"]["pause_status"] == "PAUSED"


def test_master_runner_notebook_and_command_exist():
    nb = open(os.path.join(ROOT, "deployment", "notebooks", "master_runner.py")).read()
    assert nb.startswith("# Databricks notebook source") and "master.run_master" in nb and "run_date" in nb and "dry_run" in nb
    assert 'edap-master = "edap_framework.master:main"' in open(os.path.join(ROOT, "pyproject.toml")).read()


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
