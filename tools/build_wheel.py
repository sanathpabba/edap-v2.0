"""Build the edap-framework wheel: code + definitions/ + pipelines/ (as package resources), then verify the wheel's contents.

  python tools/build_wheel.py                       -> dist/edap_framework-0.1.0-py3-none-any.whl
  python tools/build_wheel.py --version-suffix abc1234   -> version 0.1.0+abc1234 (unique per build, so a cluster reinstall is never skipped)
The build runs in a temporary staging copy, so the repository stays clean."""
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def stage(dest, suffix):
    shutil.copytree(os.path.join(ROOT, "edap_framework"), os.path.join(dest, "edap_framework"), ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "_resources"))
    for f in ("pyproject.toml", "README.md"):
        shutil.copy(os.path.join(ROOT, f), dest)
    res = os.path.join(dest, "edap_framework", "_resources")
    for d in ("definitions", "pipelines"):
        shutil.copytree(os.path.join(ROOT, d), os.path.join(res, d), ignore=IGNORE)
    init = os.path.join(dest, "edap_framework", "__init__.py")
    text = open(init).read()
    if suffix:
        text = re.sub(r'__version__ = "([^"+]+)[^"]*"', r'__version__ = "\1+%s"' % suffix, text)
        open(init, "w").write(text)
    return re.search(r'__version__ = "([^"]+)"', text).group(1)


def verify(wheel):
    """The wheel must contain every definition and pipeline step file of the repository, and the console commands."""
    z = zipfile.ZipFile(wheel)
    names = set(z.namelist())
    problems = []
    for d in ("definitions", "pipelines"):
        for base, _, files in os.walk(os.path.join(ROOT, d)):
            for f in files:
                if f.startswith(".") or f.endswith(".pyc") or "__pycache__" in base:        # dotfiles (.gitkeep) are placeholders, not resources
                    continue
                rel = os.path.relpath(os.path.join(base, f), ROOT)
                if "edap_framework/_resources/%s" % rel.replace(os.sep, "/") not in names:
                    problems.append("missing in wheel: %s" % rel)
    ep = [n for n in names if n.endswith("entry_points.txt")]
    entry = z.read(ep[0]).decode() if ep else ""
    for cmd in ("edap-run", "edap-validate", "edap-master", "edap-admin"):
        if cmd not in entry:
            problems.append("console command %s missing" % cmd)
    if "edap_framework/cli.py" not in names:
        problems.append("edap_framework/cli.py missing")
    return problems, len([n for n in names if "/_resources/pipelines/" in n and n.endswith(".py")])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist")
    ap.add_argument("--version-suffix", default="", help="local version suffix, e.g. the git sha")
    a = ap.parse_args()
    out = os.path.abspath(os.path.join(ROOT, a.out))
    os.makedirs(out, exist_ok=True)
    for old in glob.glob(os.path.join(out, "edap_framework-*.whl")):
        os.remove(old)
    with tempfile.TemporaryDirectory() as tmp:
        version = stage(tmp, a.version_suffix)
        subprocess.run([sys.executable, "-m", "build", "--wheel", "--outdir", out, tmp], check=True)
    wheel = glob.glob(os.path.join(out, "edap_framework-*.whl"))[0]
    problems, steps = verify(wheel)
    if problems:
        print("WHEEL CHECK FAILED:\n  " + "\n  ".join(problems[:20]))
        sys.exit(1)
    print("built %s (version %s, %d pipeline step files, definitions + pipelines bundled)" % (os.path.relpath(wheel, ROOT), version, steps))


if __name__ == "__main__":
    main()
