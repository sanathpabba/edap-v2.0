import os
import re
import shutil

import pytest

from edap_framework.core import config
from edap_framework.core.validator import validate
from edap_framework.pipeline.context import PipelineContext
from edap_framework.pipeline.sequence import discover, run_sequence

FOLDERS = ["Equities", "FixedIncome", "FX", "Commodities", "Common"]


def test_asset_classes_are_the_requested_folders():
    assert sorted(a.folder for a in config.list_asset_classes()) == sorted(FOLDERS)


def test_every_asset_class_has_bronze_silver_gold_with_routine_and_adhoc_per_table():
    for a in config.list_asset_classes():
        for layer in ("bronze", "silver", "gold"):
            assert a.items.get(layer), (a.folder, layer)
            for item in a.items[layer]:
                for mode in ("Routine", "Adhoc"):
                    d = os.path.join(config.project_root(), "pipelines", a.folder, layer, config.table_folder(layer, item), mode)
                    assert 8 <= len(discover(d)) <= 10, d


def test_table_folder_naming():
    assert config.table_folder("bronze", "sql-loads/trades") == "sql_trades"
    assert config.table_folder("bronze", "file-loads/positions") == "file_positions"
    assert config.table_folder("landing", "stream-loads/trade_events") == "stream_trade_events"
    assert config.table_folder("silver", "trade") == "trade" and config.table_folder("gold", "pnl_finance") == "pnl_finance"


def test_table_folders_on_disk_match_asset_class_items_exactly():
    for a in config.list_asset_classes():
        for layer, items in a.items.items():
            on_disk = set(os.listdir(os.path.join(config.project_root(), "pipelines", a.folder, layer))) - {"__pycache__"}
            assert on_disk == {config.table_folder(layer, i) for i in items}, (a.folder, layer)


def test_common_has_landing_and_asset_classes_do_not():
    assert os.path.isdir(os.path.join(config.project_root(), "pipelines", "Common", "landing", "sql_trades", "Routine"))
    assert not os.path.exists(os.path.join(config.project_root(), "pipelines", "Equities", "landing"))


def test_step_files_are_thin_and_call_one_framework_function():
    d = os.path.join(config.project_root(), "pipelines", "Equities", "bronze", "sql_trades", "Routine")
    for f in os.listdir(d):
        if f.endswith(".py"):
            text = open(os.path.join(d, f)).read()
            assert len(re.findall(r"steps\.\w+\(ctx\)", text)) == 1 and len(text.splitlines()) < 25


def test_expanded_table_names_per_asset_class():
    for a in config.list_asset_classes(include_common=False):
        m = config.load_yaml("definitions/mappings/trade.yml", a.variables())
        assert m["target"]["table"] == "%s_trade" % a.prefix
        assert m["source"]["bronze_table"] == "edap.bronze.%s_sql_trades" % a.prefix
        assert "edap.silver.common_account" in str(m["lookups"])


def test_instrument_mapping_filters_by_asset_class_types():
    m = config.load_yaml("definitions/mappings/instrument.yml", config.get_asset_class("Equities").variables())
    assert m["source"]["where"] == "upper(trim(sec_type)) IN ('EQUITY','DERIVATIVE')"
    assert config.load_yaml("definitions/mappings/instrument.yml", config.get_asset_class("FX").variables())["source"]["where"].endswith("('FX')")


def test_gold_product_sql_is_asset_class_specific():
    from edap_framework.gold.builder import compose_sql
    p = config.load_yaml("definitions/gold_products/trade_analytics.yml", config.get_asset_class("Commodities").variables())
    sql = compose_sql(p)
    assert "edap.silver.commodities_trade t" in sql and "edap.gold.common_fx_rate_daily f" in sql and "equities" not in sql


def test_dry_run_plans_every_step_in_order():
    ctx = PipelineContext("Equities", "silver", "Routine", spark=None, env={"catalog": "edap"})
    lines = []
    n = run_sequence(ctx, dry_run=True, out=lines.append)
    assert n == 4 * 10 and [l.split()[0] for l in lines if re.match(r"^\s+\d\d ", l)][:10] == ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]
    assert any("-- table: silver/trade/Routine" in l for l in lines)


def test_item_filter_accepts_table_folder_or_spec_item():
    ctx = PipelineContext("Equities", "bronze", "Routine", spark=None, env={"catalog": "edap"})
    for sel in ({"file_positions"}, {"file-loads/positions"}):
        lines = []
        assert run_sequence(ctx, sel, dry_run=True, out=lines.append) == 10
        assert any("bronze/file_positions/Routine" in l for l in lines)


def test_common_runs_first_and_all_selects_every_pipeline():
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_cli", os.path.join(config.project_root(), "pipelines", "run.py"))
    cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
    names = [a.folder for a in cli.pipelines_for("ALL", "bronze")]
    assert names[0] == "Common" and set(names) == set(FOLDERS)
    assert [a.folder for a in cli.pipelines_for("ALL", "landing")] == ["Common"]


@pytest.fixture
def broken_tree(tmp_path):
    for d in ("definitions", "pipelines", "edap_framework/pipeline"):
        shutil.copytree(os.path.join(config.project_root(), d), tmp_path / d)
    old = config._ROOT
    config._ROOT = str(tmp_path)
    yield tmp_path
    config._ROOT = old


def test_validator_catches_missing_step_file(broken_tree):
    os.remove(broken_tree / "pipelines/FX/silver/trade/Routine/04_apply_canonical_mapping.py")
    assert any("FX/silver/trade/Routine" in e for e in validate()[0])


def test_validator_catches_step_calling_unknown_function(broken_tree):
    p = broken_tree / "pipelines/FX/gold/trade_analytics/Adhoc/05_compose_sql.py"
    p.write_text(p.read_text().replace("steps.compose_sql(ctx)", "steps.does_not_exist(ctx)"))
    assert any("does_not_exist" in e for e in validate()[0])


def test_validator_catches_routine_adhoc_mismatch(broken_tree):
    p = broken_tree / "pipelines/FX/gold/trade_analytics/Adhoc/05_compose_sql.py"
    p.write_text(p.read_text().replace("steps.compose_sql(ctx)", "steps.check_upstream(ctx)"))
    assert any("differ" in e or "file name does not match" in e for e in validate()[0])


def test_validator_catches_overlapping_routing(broken_tree):
    p = broken_tree / "definitions/asset_classes/fx.yml"
    p.write_text(p.read_text().replace("sec_types: [FX]", "sec_types: [FX, BOND]"))
    assert any("routed to both" in e for e in validate()[0])


def test_validator_catches_unrouted_security_type(broken_tree):
    p = broken_tree / "definitions/asset_classes/commodities.yml"
    p.write_text(p.read_text().replace("sec_types: [COMMODITY]", "sec_types: []"))
    assert any("routing" in e for e in validate()[0])


def test_validator_catches_two_unresolved_receivers(broken_tree):
    p = broken_tree / "definitions/asset_classes/fx.yml"
    p.write_text(p.read_text().replace("receives_unresolved: false", "receives_unresolved: true"))
    assert any("receives_unresolved" in e for e in validate()[0])


def test_validator_catches_item_without_spec(broken_tree):
    p = broken_tree / "definitions/asset_classes/fx.yml"
    p.write_text(p.read_text().replace("gold: [trade_analytics,", "gold: [nonexistent_product, trade_analytics,"))
    assert any("nonexistent_product" in e for e in validate()[0])


def test_validator_catches_missing_table_folder(broken_tree):
    shutil.rmtree(broken_tree / "pipelines/FX/bronze/sql_trades")
    assert any("FX/bronze/sql_trades" in e and "missing" in e for e in validate()[0])


def test_validator_catches_orphan_table_folder(broken_tree):
    shutil.copytree(broken_tree / "pipelines/FX/silver/trade", broken_tree / "pipelines/FX/silver/not_listed")
    assert any("not_listed" in e and "not listed" in e for e in validate()[0])


def test_validator_catches_wrong_item_in_step_file(broken_tree):
    p = broken_tree / "pipelines/FX/silver/trade/Routine/03_read_bronze_increment.py"
    p.write_text(p.read_text().replace('ITEM = "trade"', 'ITEM = "position"'))
    assert any("ITEM must be" in e for e in validate()[0])


def test_validator_catches_owner_without_contact_entry(broken_tree):
    p = broken_tree / "definitions/governance/notifications.yml"
    p.write_text(p.read_text().replace("  portfolio-data-owner: {email: \"\"}\n", ""))
    assert any("portfolio-data-owner" in e and "no entry in owners" in e for e in validate()[0])


def test_validator_catches_bad_gate_limit(broken_tree):
    p = broken_tree / "definitions/bronze/file-loads/positions.yml"
    p.write_text(p.read_text().replace("max_error_rate: 0.5", "max_error_rate: 1.5"))
    assert any("max_error_rate" in e for e in validate()[0])


def test_validator_catches_file_header_drift(broken_tree):
    p = broken_tree / "definitions/landing/file-loads/positions.yml"
    p.write_text(p.read_text().replace("position_id, position_date,", "position_id,"))
    assert any("file_checks.header differs" in e for e in validate()[0])


def test_validator_catches_unknown_source_drop_container(broken_tree):
    p = broken_tree / "definitions/environments/dev.yml"
    p.write_text(p.read_text().replace("sourcedrop: sourcedrop, ", ""))
    assert any("source_drop container" in e for e in validate()[0])
