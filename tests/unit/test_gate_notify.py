import datetime as dt

import pytest

from edap_framework.core import config
from edap_framework.dq.gate import evaluate, gate_settings
from edap_framework.ingestion.files.arrival import check_expected_file, header_problems, previous_business_day
from edap_framework.notify import notifier
from edap_framework.pipeline import common
from edap_framework.pipeline.context import PipelineContext

G = gate_settings()
HEADER = ["position_id", "position_date", "portfolio_ref", "instrument_code", "position_qty", "avg_cost", "market_value", "ccy", "source_system"]


# ---- gate: only a whole-batch failure halts
def test_a_few_bad_rows_warn_but_do_not_halt():
    d = evaluate({"total": 1312, "failed_rows": 41, "warned": 0}, G)
    assert d.status == "WARN" and not d.halt


def test_mostly_bad_batch_halts():
    d = evaluate({"total": 100, "failed_rows": 50, "warned": 0}, G)
    assert d.status == "HALT" and "whole batch is treated as wrong" in d.reasons[0]


def test_empty_batch_halts_and_clean_batch_passes():
    assert evaluate({"total": 0}, G).halt
    assert evaluate({"total": 10, "failed_rows": 0, "warned": 0}, G).status == "PASS"


def test_table_gate_overrides_default_limit():
    assert evaluate({"total": 100, "failed_rows": 20}, gate_settings({"max_error_rate": 0.1})).halt
    assert not evaluate({"total": 100, "failed_rows": 20}, G).halt


# ---- file checks
def test_header_check_reports_missing_extra_and_order():
    assert header_problems(",".join(HEADER), HEADER) == []
    assert "missing column" in header_problems("position_id,position_date", HEADER)[0]
    assert any("unexpected" in p for p in header_problems(",".join(HEADER + ["junk"]), HEADER))
    assert "different order" in header_problems(",".join(reversed(HEADER)), HEADER)[0]


def test_previous_business_day_skips_weekends():
    assert previous_business_day(dt.date(2026, 11, 16)) == dt.date(2026, 11, 13)      # Monday -> Friday
    assert previous_business_day(dt.date(2026, 11, 18)) == dt.date(2026, 11, 17)


def test_file_not_received_detection():
    spec = {"file_checks": {"expected_file": {"pattern": "positions_{date}.csv", "business_date": "previous_business_day"}}}
    today = dt.date(2026, 11, 18)
    assert check_expected_file(spec, [{"business_date": "20261117"}], today) is None
    msg = check_expected_file(spec, [{"business_date": "20261116"}, {"business_date": None}], today)
    assert "positions_20261117.csv" in msg and "not received" in msg
    assert check_expected_file({}, [], today) is None


# ---- notifier
EVENT = {"kind": "DQ_WARN", "severity": "WARN", "pipeline": {"asset_class": "Equities", "layer": "bronze", "table": "file_positions", "mode": "Routine"},
         "run_id": "r1", "batch_id": "b1", "owner": "portfolio-data-owner", "headline": "41 of 1312 rows failed data quality",
         "reasons": ["3.1% quarantined"], "rules": [{"rule": "missing_portfolio", "criticality": "error", "failed_rows": 10, "total_rows": 1312}],
         "samples": [{"rules": ["missing_portfolio"], "record": '{"position_id": "POS-1"}'}], "counts": {"rows checked": 1312}, "links": ["SELECT 1"]}


def test_email_lists_the_failed_checks():
    subject, text, html = notifier.build_message(EVENT)
    assert subject.startswith("[EDAP] WARNING: Equities / bronze / file_positions")
    assert "missing_portfolio | error | 10 / 1312" in text and "POS-1" in text and "continued" in text
    assert "<table" in html and "missing_portfolio" in html


def test_halt_email_says_downstream_not_started_and_escapes_html():
    ev = {**EVENT, "severity": "HALT", "headline": "bad <file>"}
    subject, text, html = notifier.build_message(ev)
    assert "HALTED" in subject and "NOT started" in text and "&lt;file&gt;" in html


def test_recipient_resolution_and_fallback():
    cfg = {"owners": {"a": {"email": "a@x.com"}, "b": {"email": ""}}, "fallback_recipients": ["dq@x.com"]}
    assert notifier.resolve_recipients("a", cfg) == ["a@x.com"]
    assert notifier.resolve_recipients("b", cfg) == ["dq@x.com"] and notifier.resolve_recipients("zzz", cfg) == ["dq@x.com"]
    assert notifier.resolve_recipients("b", {"owners": {}, "fallback_recipients": []}) == []


def test_nothing_is_sent_until_email_is_configured():
    assert notifier.notify(None, {"catalog": "edap"}, EVENT) == "NOT_SENT_EMAIL_NOT_CONFIGURED"
    assert notifier.notify(None, {"catalog": "edap"}, EVENT, send=False) == "SUPPRESSED"


# ---- gate + notify wiring on a context (no Spark)
def _ctx(mode="Routine"):
    c = PipelineContext("Equities", "bronze", mode, spark=None, env=config.load_env())
    c.item = "file-loads/positions"
    c.st["spec"] = {"governance": {"owner": "portfolio-data-owner"}}
    return c


def test_gate_and_notify_halts_whole_batch_and_emails():
    c = _ctx()
    stats = {"total": 100, "failed_rows": 80, "warned": 0, "rules": [{"rule": "x", "criticality": "error", "failed_rows": 80, "total_rows": 100}], "samples": []}
    assert common.gate_and_notify(c, [stats], None, "edap.bronze.equities_file_positions", "bronze") == "HALT"
    assert c.st["notifications"][0][:2] == ("DQ_HALT", "HALT")


def test_gate_and_notify_warns_but_continues_for_row_level_failures():
    c = _ctx()
    stats = {"total": 1312, "failed_rows": 41, "warned": 0, "rules": [], "samples": []}
    assert common.gate_and_notify(c, [stats], None, "t", "bronze") == "WARN"
    assert c.st["notifications"][0][1] == "WARN"


def test_clean_batch_sends_nothing():
    c = _ctx()
    assert common.gate_and_notify(c, [{"total": 5, "failed_rows": 0, "warned": 0}], None, "t", "bronze") == "PASS"
    assert "notifications" not in c.st


def test_adhoc_runs_are_quiet_unless_asked():
    c = _ctx("Adhoc")
    common.gate_and_notify(c, [{"total": 100, "failed_rows": 90}], None, "t", "bronze")
    assert c.st["notifications"][0][2] == "SUPPRESSED"
    c2 = _ctx("Adhoc"); c2.params = {"notify": "true"}
    common.gate_and_notify(c2, [{"total": 100, "failed_rows": 90}], None, "t", "bronze")
    assert c2.st["notifications"][0][2] != "SUPPRESSED"


def test_notify_on_filters_severities():
    c = _ctx(); c.st["spec"]["gate"] = {"notify_on": ["halt"]}
    common.gate_and_notify(c, [{"total": 1312, "failed_rows": 41}], c.st["spec"]["gate"], "t", "bronze")
    assert "notifications" not in c.st


def test_owner_comes_from_the_spec():
    assert common.owner_of(_ctx()) == "portfolio-data-owner"


# ---- halting in the sequence: only the failing table stops; others finish; the halt is re-raised at the end
def test_halt_stops_only_that_table_and_is_reraised(monkeypatch):
    from edap_framework.pipeline import sequence
    ran = []

    class Mod:
        def __init__(self, order): self.order = order
        def run(self, ctx):
            ran.append((ctx.item, self.order))
            if ctx.item == "sql-loads/trades" and self.order == 3:
                raise common.PipelineHalt("whole file wrong")

    monkeypatch.setattr(sequence, "_load", lambda path: Mod(int(path.split("/")[-1][:2])))
    ctx = PipelineContext("Equities", "bronze", "Routine", spark=None, env={"catalog": "edap"})
    with pytest.raises(common.PipelineHalt) as e:
        sequence.run_sequence(ctx, out=lambda *_: None)
    assert "sql_trades" in str(e.value)
    assert max(o for i, o in ran if i == "sql-loads/trades") == 3                    # stopped at the halt
    assert max(o for i, o in ran if i == "file-loads/positions") == 10               # others ran to the end
    assert max(o for i, o in ran if i == "stream-loads/trade_events") == 10
