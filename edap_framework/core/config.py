"""YAML loading and environment resolution. Everything the framework does is driven from definitions/*.yml."""
import os
import yaml

def _resolve_root():
    """Where definitions/ and pipelines/ live: $EDAP_PROJECT_ROOT, else the repository checkout, else the copy bundled inside the installed wheel."""
    if os.environ.get("EDAP_PROJECT_ROOT"):
        return os.environ["EDAP_PROJECT_ROOT"]
    package_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    repo = os.path.dirname(package_dir)
    if os.path.isdir(os.path.join(repo, "definitions")):
        return repo
    bundled = os.path.join(package_dir, "_resources")
    return bundled if os.path.isdir(os.path.join(bundled, "definitions")) else repo


_ROOT = _resolve_root()


def project_root():
    return _ROOT


class _StrictBoolLoader(yaml.SafeLoader):
    """YAML 1.1 reads on/off/yes/no as booleans, which turns a key like `on:` into True. Only true/false are booleans here."""


_StrictBoolLoader.yaml_implicit_resolvers = {
    k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:bool"] for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()}
_StrictBoolLoader.add_implicit_resolver("tag:yaml.org,2002:bool", __import__("re").compile(r"^(?:true|false)$"), list("tf"))


def load_yaml(rel_path, variables=None):
    """Load a YAML file. `variables` ({"ac": "equities", ...}) replace ${name} in the text before parsing, so one spec
    serves every asset class. Only the given names are replaced; other ${...} (e.g. product parameters) are left alone."""
    with open(os.path.join(_ROOT, rel_path)) as f:
        text = f.read()
    for k, v in (variables or {}).items():
        text = text.replace("${%s}" % k, str(v))
    return yaml.load(text, Loader=_StrictBoolLoader)


class AssetClass:
    """One pipeline (an asset class, or 'Common'): name, folder, table prefix, routed security types, items per layer."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.name, self.folder, self.prefix = cfg["name"], cfg["folder"], cfg["prefix"]
        self.sec_types, self.items = cfg.get("sec_types", []), cfg.get("items", {})
        self.receives_unresolved = bool(cfg.get("receives_unresolved"))

    def variables(self):
        return {"ac": self.prefix, "asset_class": self.name, "sec_types": ",".join("'%s'" % t for t in self.sec_types) or "''"}


def list_asset_classes(include_common=True):
    d = os.path.join(_ROOT, "definitions", "asset_classes")
    out = [AssetClass(load_yaml("definitions/asset_classes/%s" % f)) for f in sorted(os.listdir(d)) if f.endswith(".yml")]
    return [a for a in out if include_common or a.prefix != "common"]


def get_asset_class(folder_or_prefix):
    for a in list_asset_classes():
        if folder_or_prefix in (a.folder, a.prefix, a.name):
            return a
    raise KeyError("unknown asset class %s" % folder_or_prefix)


def load_env(name=None):
    return load_yaml("definitions/environments/%s.yml" % (name or os.environ.get("EDAP_ENV", "dev")))


def load_spec(layer, source_folder, table, variables=None):
    """definitions/<layer>/<source_folder>/<table>.yml  e.g. ('bronze', 'sql-loads', 'trades')"""
    return load_yaml("definitions/%s/%s/%s.yml" % (layer, source_folder, table), variables)


def list_tables(layer, source_folder):
    d = os.path.join(_ROOT, "definitions", layer, source_folder)
    return sorted(f[:-4] for f in os.listdir(d) if f.endswith(".yml"))


def storage_uri(env, container, path=""):
    st = env["storage"]
    return st["uri_template"].format(container=st["containers"][container], account=st["account"], path=path.lstrip("/"))


def table_folder(layer, item):
    """Folder name of a table/entity/product inside pipelines/<AssetClass>/<layer>/.
    landing/bronze items are '<source>-loads/<table>' -> '<source>_<table>' (e.g. sql-loads/trades -> sql_trades);
    silver/gold items are already plain names (trade, trade_analytics)."""
    if "/" in item:
        src, table = item.split("/", 1)
        return "%s_%s" % (src.replace("-loads", ""), table)
    return item
