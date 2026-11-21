"""YAML loading and environment resolution. Everything the framework does is driven from definitions/*.yml."""
import os
import yaml

_ROOT = os.environ.get("EDAP_PROJECT_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def project_root():
    return _ROOT


class _StrictBoolLoader(yaml.SafeLoader):
    """YAML 1.1 reads on/off/yes/no as booleans, which turns a key like `on:` into True. Only true/false are booleans here."""


_StrictBoolLoader.yaml_implicit_resolvers = {
    k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:bool"] for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()}
_StrictBoolLoader.add_implicit_resolver("tag:yaml.org,2002:bool", __import__("re").compile(r"^(?:true|false)$"), list("tf"))


def load_yaml(rel_path):
    with open(os.path.join(_ROOT, rel_path)) as f:
        return yaml.load(f, Loader=_StrictBoolLoader)


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
