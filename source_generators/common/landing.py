"""ADLS Gen2 landing helpers (az CLI, signed-in user; no keys)."""
import subprocess

ACCOUNT, CONTAINER = "edapdl", "landing"
SOURCE_CONTAINER = "sourcedrop"      # stand-in for the source system's own storage; the landing pipeline copies files from here into landing


def _az(*args):
    return subprocess.run(["az", "storage", "fs"] + list(args) + ["--account-name", ACCOUNT, "--auth-mode", "login"],
                          capture_output=True, text=True)


def ensure_source_container():
    subprocess.run(["az", "storage", "fs", "create", "-n", SOURCE_CONTAINER, "--account-name", ACCOUNT, "--auth-mode", "login"], capture_output=True, text=True)


def upload_source(local, remote):
    """Drop a file into the (simulated) source system storage."""
    ensure_source_container()
    r = _az("file", "upload", "-f", SOURCE_CONTAINER, "-p", remote, "-s", local, "--overwrite", "true")
    if r.returncode:
        raise RuntimeError("source drop upload failed for %s: %s" % (remote, r.stderr[:300]))


def list_source(prefix):
    r = _az("file", "list", "-f", SOURCE_CONTAINER, "--path", prefix, "--query", "[?!isDirectory].name", "-o", "tsv")
    return [x for x in r.stdout.split("\n") if x]


def clear_source(prefix):
    for f in list_source(prefix):
        _az("file", "delete", "-f", SOURCE_CONTAINER, "-p", f, "--yes")


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
