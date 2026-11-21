import os

from edap_framework.core import config
from edap_framework.gold.builder import compose_sql, resolve_parameters

EQ = config.get_asset_class("Equities").variables()


def test_regulatory_sql_has_parameters_substituted():
    sql = compose_sql(config.load_yaml("definitions/gold_products/regulatory_reporting.yml", EQ))
    assert "${" not in sql and ">= 50000000" in sql and "'v1' AS report_version" in sql


def test_adhoc_parameter_override_changes_the_sql():
    p = config.load_yaml("definitions/gold_products/regulatory_reporting.yml", EQ)
    sql = compose_sql(p, resolve_parameters(p, {"large_exposure_threshold_usd": "1000"}))
    assert ">= 1000" in sql and "50000000" not in sql


def test_fx_dimension_uses_cross_join_without_on():
    sql = compose_sql(config.load_yaml("definitions/gold_products/fx_rate_daily.yml", config.get_asset_class("Common").variables()))
    assert "CROSS JOIN ccy y\n" in sql and "last_value(m.usd_per_unit, true)" in sql and "edap.silver.common_market_data" in sql


def test_every_product_composes_for_every_asset_class():
    for a in config.list_asset_classes():
        for item in a.items.get("gold", []):
            sql = compose_sql(config.load_yaml("definitions/gold_products/%s.yml" % item, a.variables()))
            assert "${" not in sql.replace("${large_exposure_threshold_usd}", "") and " AS " in sql
