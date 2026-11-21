"""Execute the Spark-free steps for every asset class and item, to catch wiring errors (missing keys, bad paths) without a cluster."""
from edap_framework.core import config
from edap_framework.pipeline import bronze_steps, gold_steps, landing_steps, silver_steps
from edap_framework.pipeline.context import PipelineContext


def _ctx(ac, layer, mode="Routine", item=None):
    c = PipelineContext(ac, layer, mode, spark=None, env=config.load_env())
    c.item = item
    return c


def test_landing_specs_load_for_every_item():
    for a in config.list_asset_classes():
        for item in a.items.get("landing", []):
            c = _ctx(a, "landing", item=item)
            landing_steps.read_source_yaml(c)
            assert c.st["spec"]["layer"] == "landing" and c.st["source"]


def test_bronze_specs_resolve_for_every_asset_class_item_and_mode():
    for a in config.list_asset_classes():
        for mode in ("Routine", "Adhoc"):
            for item in a.items.get("bronze", []):
                c = _ctx(a, "bronze", mode, item)
                bronze_steps.read_source_yaml(c)
                assert c.st["fq"] == "edap.bronze.%s_%s" % (a.prefix, c.st["spec"]["target"]["table"].split("%s_" % a.prefix)[1])
                assert c.st["spec"]["checkpoint"]["path"].startswith("_checkpoints/%s_" % a.prefix)


def test_instrument_routing_only_in_asset_class_pipelines():
    for a in config.list_asset_classes():
        for item in a.items.get("bronze", []):
            c = _ctx(a, "bronze", item=item); bronze_steps.read_source_yaml(c)
            routed = c.st["spec"]["scope"]["by"] == "instrument"
            assert routed == (a.prefix != "common")


def test_silver_mappings_resolve_everywhere():
    for a in config.list_asset_classes():
        for item in a.items.get("silver", []):
            c = _ctx(a, "silver", item=item)
            silver_steps.read_mapping_yaml(c)
            assert c.st["fq"] == "edap.silver.%s_%s" % (a.prefix, item)


def test_gold_steps_compose_for_everything_and_override_in_adhoc():
    for a in config.list_asset_classes():
        for item in a.items.get("gold", []):
            c = _ctx(a, "gold", "Routine", item)
            gold_steps.read_product_yaml(c); gold_steps.resolve_parameters(c); gold_steps.compose_sql(c)
            assert c.st["fq"] == "edap.gold.%s_%s" % (a.prefix, item) and "SELECT" in c.st["sql"]
    c = _ctx("Equities", "gold", "Adhoc", "regulatory_reporting")
    c.params = {"product_params": {"large_exposure_threshold_usd": "5"}}
    gold_steps.read_product_yaml(c); gold_steps.resolve_parameters(c); gold_steps.compose_sql(c)
    assert ">= 5" in c.st["sql"]
