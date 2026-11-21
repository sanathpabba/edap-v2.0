import re

import pytest
import yaml

from edap_framework import master
from edap_framework.cli import stage_selected
from edap_framework.consumption import builder
from edap_framework.core import config

EQ = config.get_asset_class("Equities")


def _spec(name, ac=EQ):
    return config.load_yaml("definitions/consumption/%s.yml" % name, ac.variables())


# ---------------- consumption builder
def test_metric_view_statement_is_valid_yaml_inside_create_with_metrics():
    stmt = builder.compose_statement(_spec("trade_metrics"))
    assert stmt.startswith("CREATE OR REPLACE VIEW edap.consumption.equities_trade_metrics\nWITH METRICS\nLANGUAGE YAML\nAS $$\n")
    body = yaml.safe_load(stmt.split("AS $$\n")[1].rsplit("$$", 1)[0])
    assert body["version"] == 1.1 and body["source"] == "edap.gold.equities_trade_analytics"
    names = [m["name"] for m in body["measures"]]
    assert "Trade Count" in names and "Failure Rate" in names
    assert body["dimensions"][0] == {"name": "Trade Date", "expr": "trade_date"}


def test_measure_references_resolve_in_every_metric_view_and_asset_class():
    for a in config.list_asset_classes(include_common=False):
        for item in a.items["consumption"]:
            spec = _spec(item, a)
            if spec["kind"] != "metric_view":
                continue
            names = {m["name"] for m in spec["metric_view"]["measures"]}
            for m in spec["metric_view"]["measures"]:
                assert set(re.findall(r"MEASURE\(`([^`]+)`\)", m["expr"])) <= names, (a.folder, item, m["name"])


def test_materialized_view_is_created_then_refreshed_and_rebuilt_on_request():
    spec = _spec("trade_daily_mv")
    first = builder.compose_statement(spec, exists=False)
    assert first.startswith("CREATE OR REPLACE MATERIALIZED VIEW edap.consumption.equities_trade_daily_mv\nCOMMENT '") and "FROM edap.gold.equities_trade_analytics" in first
    assert builder.compose_statement(spec, exists=True) == "REFRESH MATERIALIZED VIEW edap.consumption.equities_trade_daily_mv"
    assert builder.compose_statement(spec, exists=True, rebuild=True).startswith("CREATE OR REPLACE MATERIALIZED VIEW")


def test_verify_statements():
    assert builder.verify_statement(_spec("trade_metrics")) == "SELECT MEASURE(`Trade Count`) FROM edap.consumption.equities_trade_metrics"
    assert builder.verify_statement(_spec("trade_daily_mv")) == "SELECT COUNT(*) FROM edap.consumption.equities_trade_daily_mv"


def test_unknown_kind_is_rejected():
    spec = _spec("trade_metrics"); spec["kind"] = "table"
    with pytest.raises(ValueError):
        builder.compose_statement(spec)


def test_run_sql_uses_spark_unless_a_warehouse_is_configured():
    class R:
        def collect(self): return [(7,)]

    class S:
        def __init__(self): self.sql_calls = []
        def sql(self, q): self.sql_calls.append(q); return R()

    s = S()
    assert builder.run_sql(s, {"catalog": "edap"}, "SELECT 1") == [(7,)] and s.sql_calls == ["SELECT 1"]
    assert builder.run_sql(s, {"catalog": "edap", "consumption": {"sql_warehouse_id": ""}}, "SELECT 2") == [(7,)]


def test_every_asset_class_has_the_four_consumption_objects_with_own_names():
    seen = set()
    for a in config.list_asset_classes(include_common=False):
        assert a.items["consumption"] == ["trade_metrics", "exposure_metrics", "trade_daily_mv", "portfolio_exposure_mv"]
        for item in a.items["consumption"]:
            fq = builder.fq_name(_spec(item, a))
            assert fq.startswith("edap.consumption.%s_" % a.prefix) and fq not in seen
            seen.add(fq)
    assert len(seen) == 16


# ---------------- CLI stage filter
def test_stage_filter():
    assert stage_selected("gold", "") and stage_selected("gold", None)
    assert stage_selected("gold", "bronze, gold") and not stage_selected("consumption", "bronze,silver,gold")


# ---------------- master runner (fake Databricks jobs API)
class _Enum:
    def __init__(self, value): self.value = value


class FakeRun:
    def __init__(self, life, result, tasks=()):
        self.state = type("S", (), {"life_cycle_state": _Enum(life), "result_state": _Enum(result) if result else None})()
        self.run_page_url = "https://example/run"
        self.tasks = [type("T", (), {"task_key": k, "state": type("S", (), {"result_state": _Enum(r)})()})() for k, r in tasks]


class FakeJobs:
    def __init__(self, names, outcome=None):
        self.names, self.outcome, self.triggered, self.polls = names, outcome or {}, [], {}
        self.jobs_by_id = {i + 100: n for i, n in enumerate(names)}

    def list(self):
        return [type("J", (), {"job_id": i, "created_time": i, "settings": type("St", (), {"name": n})()})() for i, n in self.jobs_by_id.items()]

    def run_now(self, job_id, job_parameters):
        self.triggered.append((self.jobs_by_id[job_id], job_parameters))
        return type("W", (), {"run_id": job_id * 10})()

    def get_run(self, run_id):
        name = self.jobs_by_id[run_id // 10]
        self.polls[name] = self.polls.get(name, 0) + 1
        if self.polls[name] < 2:
            return FakeRun("RUNNING", None)
        result = self.outcome.get(name, "SUCCESS")
        return FakeRun("TERMINATED", result, [("bronze", "SUCCESS"), ("silver", result)])


class FakeW:
    def __init__(self, names, outcome=None): self.jobs = FakeJobs(names, outcome)


NAMES = ["[dev edap_ci] edap-common", "[dev edap_ci] edap-equities", "[dev edap_ci] edap-fixedincome", "[dev edap_ci] edap-fx", "[dev edap_ci] edap-commodities"]


def test_plan_runs_common_first_then_asset_classes_in_parallel():
    plan = master.build_plan("ALL", "")
    assert [[a.folder for a in w] for w in plan["waves"]] == [["Common"], ["Commodities", "Equities", "FX", "FixedIncome"]]
    assert [[a.folder for a in w] for w in master.build_plan("Equities,fx", "silver,gold")["waves"]] == [["Equities", "FX"]]
    assert [[a.folder for a in w] for w in master.build_plan("ALL", "landing")["waves"]] == [["Common"]]       # only Common has landing
    assert [[a.folder for a in w] for w in master.build_plan("ALL", "consumption")["waves"]] == [["Commodities", "Equities", "FX", "FixedIncome"]]


def test_unknown_inputs_are_refused():
    with pytest.raises(master.MasterFailed, match="unknown asset class"):
        master.build_plan("Bonds", "")
    with pytest.raises(master.MasterFailed, match="unknown stage"):
        master.build_plan("ALL", "bronze,platinum")
    with pytest.raises(master.MasterFailed, match="mode"):
        master.job_parameters(["gold"], "Nightly")


def test_adhoc_does_not_expect_a_file_unless_asked_and_extra_tokens():
    assert master.job_parameters(["gold"], "Routine")["expect_file"] == "true"
    assert master.job_parameters(["gold"], "Adhoc")["expect_file"] == "false"
    assert master.job_parameters(["gold"], "Adhoc", expect_file="true")["expect_file"] == "true"
    assert master.extra_tokens("2026-11-17T00:00:00", "", "history", True, False, True, "a=1 b=2") == "from_ts=2026-11-17T00:00:00 fx_mode=history rescan=true notify=true a=1 b=2"
    assert master.extra_tokens() == ""


def test_dev_prefixed_job_names_are_found_and_missing_jobs_are_reported():
    w = FakeW(NAMES)
    assert master.find_job_id(w, "edap-equities") == 101
    with pytest.raises(master.MasterFailed, match="not found"):
        master.find_job_id(FakeW(["other"]), "edap-equities")


def test_dry_run_checks_jobs_and_triggers_nothing():
    w = FakeW(NAMES)
    out = master.run_master(w, "ALL", "", "Routine", "2026-11-17", dry_run=True, log=lambda *_: None)
    assert out["dry_run"] and w.jobs.triggered == [] and set(out["job_ids"]) == {"Common", "Equities", "FixedIncome", "FX", "Commodities"}


def test_master_triggers_common_then_all_asset_classes_with_the_parameters():
    w = FakeW(NAMES)
    out = master.run_master(w, "ALL", "bronze,silver", "Routine", "2026-11-17", extra="notify=true", poll_seconds=0, sleep=lambda s: None, log=lambda *_: None)
    order = [n.replace("[dev edap_ci] ", "") for n, _ in w.jobs.triggered]
    assert order[0] == "edap-common" and sorted(order[1:]) == ["edap-commodities", "edap-equities", "edap-fixedincome", "edap-fx"]
    params = w.jobs.triggered[0][1]
    assert params == {"mode": "Routine", "stages": "bronze,silver", "date": "2026-11-17", "expect_file": "true", "extra": "notify=true"}
    assert all(r["result"] == "SUCCESS" for r in out["results"])


def test_asset_classes_are_not_started_when_common_fails_and_the_master_fails():
    w = FakeW(NAMES, outcome={"[dev edap_ci] edap-common": "FAILED"})
    logs = []
    with pytest.raises(master.MasterFailed, match="failed: Common"):
        master.run_master(w, "ALL", "", "Routine", "", poll_seconds=0, sleep=lambda s: None, log=logs.append)
    assert [n for n, _ in w.jobs.triggered] == ["[dev edap_ci] edap-common"]
    assert any("wave 2 skipped" in l for l in logs) and any("failed tasks: silver" in l for l in logs)


def test_one_asset_class_failing_is_reported_but_the_others_still_finish():
    w = FakeW(NAMES, outcome={"[dev edap_ci] edap-fx": "FAILED"})
    with pytest.raises(master.MasterFailed, match="failed: FX"):
        master.run_master(w, "ALL", "", "Routine", "", poll_seconds=0, sleep=lambda s: None, log=lambda *_: None)
    assert len(w.jobs.triggered) == 5                                           # all four asset classes ran in parallel after Common
    assert all(w.jobs.polls[n] >= 2 for n in NAMES)                             # and every run was waited for


def test_no_wait_returns_run_ids_without_polling():
    w = FakeW(NAMES)
    out = master.run_master(w, "Equities", "gold", "Routine", "", wait=False, log=lambda *_: None)
    assert out["results"][0]["run_id"] and w.jobs.polls == {}
