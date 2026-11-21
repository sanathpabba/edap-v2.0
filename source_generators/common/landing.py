"""ADLS Gen2 landing helpers (az CLI, signed-in user; no keys)."""
import subprocess

ACCOUNT, CONTAINER = "edapdl", "landing"


def _az(*args):
    return subprocess.run(["az", "storage", "fs"] + list(args) + ["--account-name", ACCOUNT, "--auth-mode", "login"],
                          capture_output=True, text=True)


def upload(local, remote):
    r = _az("file", "upload", "-f", CONTAINER, "-p", remote, "-s", local, "--overwrite", "true")
    if r.returncode:
        raise RuntimeError("upload failed for %s: %s" % (remote, r.stderr[:300]))


def list_files(prefix):
    r = _az("file", "list", "-f", CONTAINER, "--path", prefix, "--query", "[?!isDirectory].name", "-o", "tsv")
    return [x for x in r.stdout.split("\n") if x]


def clear(prefix):
    for f in list_files(prefix):
        _az("file", "delete", "-f", CONTAINER, "-p", f, "--yes")
