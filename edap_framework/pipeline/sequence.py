"""Run a pipeline folder: discover the ordinal step files (NN_name.py) and call their run(ctx) in order, for each item.

  pipelines/<AssetClass>/<layer>/<Routine|Adhoc>/01_init_context.py ... NN_*.py
Each step file only calls a framework function; the sequence lives in the file names."""
import importlib.util
import os
import re

from edap_framework.core import config

STEP_RX = re.compile(r"^(\d{2})_([a-z0-9_]+)\.py$")


def steps_dir(asset_class_folder, layer, mode):
    return os.path.join(config.project_root(), "pipelines", asset_class_folder, layer, mode)


def discover(directory):
    """[(order, name, path)] sorted by the two-digit prefix; gaps/duplicates are errors."""
    found = []
    for f in sorted(os.listdir(directory)):
        m = STEP_RX.match(f)
        if m:
            found.append((int(m.group(1)), m.group(2), os.path.join(directory, f)))
    orders = [o for o, _, _ in found]
    if orders != list(range(1, len(orders) + 1)):
        raise ValueError("%s: step numbers must run 01..NN without gaps, got %s" % (directory, orders))
    return found


def _load(path):
    spec = importlib.util.spec_from_file_location("step_" + os.path.basename(path)[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_sequence(ctx, only_items=None, first=1, last=99, dry_run=False, out=print):
    steps = [s for s in discover(steps_dir(ctx.ac.folder, ctx.layer, ctx.mode)) if first <= s[0] <= last]
    items = [i for i in ctx.items if not only_items or i in only_items]
    out("== %s  | items: %s | steps %02d-%02d" % (ctx.describe(), ", ".join(items) or "-", steps[0][0] if steps else 0, steps[-1][0] if steps else 0))
    for item in items:
        ctx.item = item
        out("-- item: %s" % item)
        for order, name, path in steps:
            out("   %02d %s" % (order, name))
            if not dry_run:
                _load(path).run(ctx)
    return len(items) * len(steps)
