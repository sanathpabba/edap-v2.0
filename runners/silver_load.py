"""Silver: build canonical entities from mapping YAMLs in dependency order (reference data first).
   python runners/silver_load.py                 # all entities
   python runners/silver_load.py --entity trade  # one entity (its dependencies must already be loaded)"""
import argparse
import os

import _bootstrap
from edap_framework.core import config
from edap_framework.silver.engine import build_entity
from edap_framework.silver.reference import list_reference, load_reference


def order(entities):
    """Topological order from each mapping's depends_on (names that are not entities, e.g. 'reference', are ignored)."""
    maps = {e: config.load_yaml("definitions/mappings/%s.yml" % e) for e in entities}
    done, out = set(), []
    while len(out) < len(maps):
        progressed = False
        for e, m in maps.items():
            if e not in done and all(d in done or d not in maps for d in m.get("depends_on", [])):
                done.add(e); out.append(e); progressed = True
        if not progressed:
            raise RuntimeError("circular depends_on in mappings")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--entity"); ap.add_argument("--scenario"); _bootstrap.add_run_id(ap)
    a = ap.parse_args(); _bootstrap.apply_run_id(a)
    spark, env = _bootstrap.spark_session(), config.load_env()
    allm = sorted(f[:-4] for f in os.listdir(os.path.join(config.project_root(), "definitions", "mappings")) if f.endswith(".yml"))
    if not a.entity:
        for n in list_reference():
            load_reference(spark, n, env)
    for e in ([a.entity] if a.entity else order(allm)):
        print(e, build_entity(spark, config.load_yaml("definitions/mappings/%s.yml" % e), env, scenario=a.scenario))
