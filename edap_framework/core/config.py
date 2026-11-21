"""YAML loading and environment resolution. Everything the framework does is driven from definitions/*.yml."""
import os
import yaml

_ROOT = os.environ.get("EDAP_PROJECT_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def project_root():
    return _ROOT


def load_yaml(rel_path):
    with open(os.path.join(_ROOT, rel_path)) as f:
        return yaml.safe_load(f)


def load_env(name=None):
    return load_yaml("definitions/environments/%s.yml" % (name or os.environ.get("EDAP_ENV", "dev")))


def load_spec(layer, source_folder, table):
    """definitions/<layer>/<source_folder>/<table>.yml  e.g. ('bronze', 'sql-loads', 'trades')"""
    return load_yaml("definitions/%s/%s/%s.yml" % (layer, source_folder, table))


def list_tables(layer, source_folder):
    d = os.path.join(_ROOT, "definitions", layer, source_folder)
    return sorted(f[:-4] for f in os.listdir(d) if f.endswith(".yml"))


def storage_uri(env, container, path=""):
    st = env["storage"]
    return st["uri_template"].format(container=st["containers"][container], account=st["account"], path=path.lstrip("/"))
