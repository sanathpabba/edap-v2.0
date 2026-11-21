"""Run a pipeline: for each table (item) of the layer, discover its ordinal step files (NN_name.py) and call their run(ctx) in order.

  pipelines/<AssetClass>/<layer>/<table>/<Routine|Adhoc>/01_init_context.py ... NN_*.py
Each table has its own folder and step files; each step file only calls a framework function. The sequence lives in the file names."""
import importlib.util
import os
import re

from edap_framework.core import config
from edap_framework.pipeline.common import PipelineHalt

STEP_RX = re.compile(r"^(\d{2})_([a-z0-9_]+)\.py$")


def steps_dir(asset_class_folder, layer, table_folder, mode):
    return os.path.join(config.project_root(), "pipelines", asset_class_folder, layer, table_folder, mode)


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
    """Run the steps of every selected table. only_items may hold spec items (file-loads/positions, trade) or table folders (file_positions).
    A PipelineHalt (whole file missing/wrong, whole batch failed DQ) stops that table only; the other tables still run, and the halts are
    re-raised together at the end so the job task fails and downstream tasks do not start."""
    wanted = lambda item: not only_items or item in only_items or config.table_folder(ctx.layer, item) in only_items
    items = [i for i in ctx.items if wanted(i)]
    out("== %s | tables: %s" % (ctx.describe(), ", ".join(config.table_folder(ctx.layer, i) for i in items) or "-"))
    total, halts = 0, []
    for item in items:
        ctx.item = item
        folder = config.table_folder(ctx.layer, item)
        steps = [s for s in discover(steps_dir(ctx.ac.folder, ctx.layer, folder, ctx.mode)) if first <= s[0] <= last]
        out("-- table: %s/%s/%s  (%s) steps %02d-%02d" % (ctx.layer, folder, ctx.mode, item, steps[0][0] if steps else 0, steps[-1][0] if steps else 0))
        for order, name, path in steps:
            out("   %02d %s" % (order, name))
            if dry_run:
                total += 1
                continue
            mod = _load(path)
            if getattr(mod, "ITEM", item) != item:
                raise RuntimeError("%s declares ITEM %s but runs for %s" % (path, mod.ITEM, item))
            try:
                mod.run(ctx)
            except PipelineHalt as halt:
                out("   !! HALTED at step %02d %s: %s" % (order, name, halt))
                halts.append("%s/%s: %s" % (ctx.layer, folder, halt))
                break
            total += 1
    if halts:
        raise PipelineHalt("%d table(s) halted - %s" % (len(halts), " | ".join(halts)))
    return total
