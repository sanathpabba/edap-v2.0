"""Pipeline context: everything a step function needs, passed from step to step.
One context = one pipeline run (asset class x layer x mode). Steps work on `ctx.item` (one table/entity/product at a time)."""
from edap_framework.core import audit, config


class PipelineContext:
    def __init__(self, asset_class, layer, mode, spark=None, env=None, scenario=None, params=None, run_id=None):
        self.ac = asset_class if isinstance(asset_class, config.AssetClass) else config.get_asset_class(asset_class)
        self.layer, self.mode = layer, mode                      # layer: landing|bronze|silver|gold ; mode: Routine|Adhoc
        self.spark, self.env = spark, env or config.load_env()
        self.scenario = scenario
        self.params = params or {}                               # adhoc/run parameters: from_ts, to_ts, landing_batch, date, full, ...
        self.batch_id = audit.new_batch_id()
        self.run_id = run_id or audit.run_id()
        self.items = list(self.ac.items.get(layer, []))
        self.item = None
        self.state = {}

    @property
    def is_adhoc(self):
        return self.mode.lower() == "adhoc"

    @property
    def st(self):
        """Mutable state of the current item (spec, dataframe, counts ...), carried between steps."""
        return self.state.setdefault(self.item, {})

    @property
    def variables(self):
        return self.ac.variables()

    def spec_path(self, layer, folder_or_name, table=None):
        return "definitions/%s/%s.yml" % (layer, "%s/%s" % (folder_or_name, table) if table else folder_or_name)

    def describe(self):
        return "%s / %s / %s" % (self.ac.folder, self.layer, self.mode)
