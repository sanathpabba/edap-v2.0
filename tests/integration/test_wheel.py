"""Build the wheel, install it into an empty directory and run it from somewhere else: proves the package is self-contained
(code + definitions + pipelines + console commands) without a repository or Spark. Needs network for the isolated build (setuptools)."""
import glob
import os
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
pytest.importorskip("build", reason="pip install build")


@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    out = tmp_path_factory.mktemp("dist")
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_wheel.py"), "--out", str(out), "--version-suffix", "pytest"],
                   check=True, cwd=ROOT, capture_output=True)
    wheel = glob.glob(str(out / "edap_framework-*.whl"))[0]
    target = tmp_path_factory.mktemp("site")
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(target), wheel], check=True, capture_output=True)
    return str(target), wheel


def _run(target, *args):
    env = {k: v for k, v in os.environ.items() if k != "EDAP_PROJECT_ROOT"}
    env["PYTHONPATH"] = target
    return subprocess.run([sys.executable, *args], cwd=target, env=env, capture_output=True, text=True)


def test_wheel_version_is_unique_per_build(installed):
    assert "+pytest" in os.path.basename(installed[1])


def test_installed_package_finds_its_bundled_definitions(installed):
    r = _run(installed[0], "-c", "from edap_framework.core import config; print(config.project_root())")
    assert r.returncode == 0 and r.stdout.strip().endswith("edap_framework/_resources")


def test_validator_passes_from_the_installed_wheel(installed):
    r = _run(installed[0], "-c", "from edap_framework.core.validator import main; main()")
    assert r.returncode == 0 and "0 error(s)" in r.stdout, r.stdout + r.stderr


def test_edap_run_plans_a_pipeline_from_the_installed_wheel(installed):
    r = _run(installed[0], "-m", "edap_framework.cli", "--asset-class", "FixedIncome", "--layer", "silver", "--mode", "Routine", "--item", "trade", "--dry-run")
    assert r.returncode == 0 and "silver/trade/Routine" in r.stdout and "10 step executions" in r.stdout, r.stdout + r.stderr
