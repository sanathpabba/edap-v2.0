import os
import shutil

import pytest

from edap_framework.core import config
from edap_framework.core.validator import rule_columns, validate


def test_all_definitions_are_consistent():
    errors, _ = validate()
    assert errors == []


def test_yaml_on_key_is_not_a_boolean():
    m = config.load_yaml("definitions/mappings/trade.yml")
    assert "on" in m["lookups"][0] and True not in m["lookups"][0]


def test_yaml_true_false_still_booleans():
    assert config.load_yaml("definitions/mappings/trade.yml")["source"]["exclude_quarantined"] is True


def test_rule_columns_reads_sql_expressions():
    rs = {"checks": [{"check": {"function": "sql_expression", "arguments": {"expression": "settle_dt >= trade_dt AND side IN ('BUY','SELL')"}}},
                     {"check": {"function": "is_unique", "arguments": {"columns": ["a", "b"]}}}]}
    assert rule_columns(rs) == {"settle_dt", "trade_dt", "side", "a", "b"}


@pytest.fixture
def broken_copy(tmp_path):
    shutil.copytree(os.path.join(config.project_root(), "definitions"), tmp_path / "definitions")
    old = config._ROOT
    config._ROOT = str(tmp_path)
    yield tmp_path
    config._ROOT = old


def _edit(path, old, new):
    s = path.read_text(); assert old in s; path.write_text(s.replace(old, new, 1))


def test_validator_catches_rule_on_missing_column(broken_copy):
    _edit(broken_copy / "definitions/dq_rules/silver/trade.yml", "column: trade_id", "column: no_such_column")
    errors, _ = validate()
    assert any("no_such_column" in e for e in errors)


def test_validator_catches_missing_rules_file(broken_copy):
    _edit(broken_copy / "definitions/bronze/sql-loads/trades.yml", "definitions/dq_rules/bronze/sql_trades.yml", "definitions/dq_rules/bronze/nope.yml")
    assert any("nope.yml" in e for e in validate()[0])


def test_validator_catches_unknown_lookup_table(broken_copy):
    _edit(broken_copy / "definitions/mappings/trade.yml", "edap.reference.trade_status", "edap.reference.not_there")
    assert any("not_there" in e for e in validate()[0])


def test_validator_catches_gold_join_to_unknown_table(broken_copy):
    _edit(broken_copy / "definitions/gold_products/trade_analytics.yml", "edap.silver.account", "edap.silver.accountz")
    assert any("accountz" in e for e in validate()[0])


def test_validator_catches_bronze_column_drift(broken_copy):
    _edit(broken_copy / "definitions/bronze/sql-loads/trades.yml", '  price: "decimal(18,6)"\n', "")
    assert any("differ" in e for e in validate()[0])


def test_validator_catches_split_decimal_type(broken_copy):
    _edit(broken_copy / "definitions/bronze/sql-loads/trades.yml", 'qty: "decimal(18,4)"', "qty: decimal(18")
    assert any("malformed type" in e for e in validate()[0])
