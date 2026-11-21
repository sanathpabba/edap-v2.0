from edap_framework.core import config
from edap_framework.gold.builder import compose_sql


def test_regulatory_sql_has_parameters_substituted():
    sql = compose_sql(config.load_yaml("definitions/gold_products/regulatory_reporting.yml"))
    assert "${" not in sql and ">= 50000000" in sql and "'v1' AS report_version" in sql


def test_fx_dimension_uses_cross_join_without_on():
    sql = compose_sql(config.load_yaml("definitions/gold_products/fx_rate_daily.yml"))
    assert "CROSS JOIN ccy y\n" in sql and "last_value(m.usd_per_unit, true)" in sql


def test_every_product_composes():
    import os
    for f in [x for x in os.listdir(os.path.join(config.project_root(), "definitions", "gold_products")) if x.endswith(".yml")]:
        sql = compose_sql(config.load_yaml("definitions/gold_products/%s" % f))
        assert sql.count("SELECT") >= 1 and " AS " in sql
