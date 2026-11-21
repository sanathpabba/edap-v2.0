"""Regression tests for the first real run: a missing source-drop folder, and one table's crash stopping the independent others."""
import datetime as dt

import pytest

from edap_framework.core import config
from edap_framework.ingestion.files import arrival
from edap_framework.pipeline import common, landing_steps, sequence
from edap_framework.pipeline.context import PipelineContext

# the real message from the failed run (SAS signature removed)
PATH_NOT_FOUND = ('(com.databricks.sql.io.CloudFileNotFoundException) Operation failed: "The specified path does not exist.", 404, GET, '
                  'https://edapdl.dfs.core.windows.net/sourcedrop?directory=positions, PathNotFound')


class FakeFs:
    def __init__(self, error=None, files=()):
        self.error, self.files = error, list(files)

    def ls(self, folder):
        if self.error:
            raise Exception(self.error)
        return self.files


class FakeDbutils:
    def __init__(self, **kw):
        self.fs = FakeFs(**kw)


class FakeSpark:
    """Just enough Spark for the file registry lookups: no tables, nothing registered."""
    def sql(self, statement):
        class R:
            def collect(self_inner):
                return []
        return R()


def _spec():
    return config.load_yaml("definitions/landing/file-loads/positions.yml", config.get_asset_class("Common").variables())


def test_missing_source_drop_folder_means_no_files_not_a_crash(monkeypatch):
    monkeypatch.setattr(arrival.spark_utils, "get_dbutils", lambda spark: FakeDbutils(error=PATH_NOT_FOUND))
    assert arrival.scan_source_drop(FakeSpark(), _spec(), config.load_env()) == []


def test_other_storage_errors_still_raise(monkeypatch):
    monkeypatch.setattr(arrival.spark_utils, "get_dbutils", lambda spark: FakeDbutils(error="403 AuthorizationPermissionMismatch"))
    with pytest.raises(Exception, match="403"):
        arrival.scan_source_drop(FakeSpark(), _spec(), config.load_env())


def test_a_dropped_file_is_listed_as_new(monkeypatch):
    class F:
        name, path, size, modificationTime = "positions_20261116.csv", "abfss://x/positions/positions_20261116.csv", 100, 1.0e12
        def isDir(self): return False
    monkeypatch.setattr(arrival.spark_utils, "get_dbutils", lambda spark: FakeDbutils(files=[F()]))
    files = arrival.scan_source_drop(FakeSpark(), _spec(), config.load_env())
    assert [f["name"] for f in files] == ["positions_20261116.csv"] and files[0]["new"] and files[0]["business_date"] == "20261116"


def test_empty_drop_with_expectation_is_the_designed_file_not_received_halt(monkeypatch):
    """Nothing in the source drop + the daily run's expect_file=true -> halt flag and an owner notification (no crash)."""
    ctx = PipelineContext("Common", "landing", "Routine", spark=None, env=config.load_env())
    ctx.item = "file-loads/positions"
    landing_steps.read_source_yaml(ctx)
    ctx.st.update({"expect_file": True, "today": dt.date(2026, 11, 21), "all_files": [], "files": [], "good": [], "bad": [], "rows": []})
    landing_steps.validate_batch(ctx)
    assert "positions_20261120.csv" in ctx.st["halt"] and "not received" in ctx.st["halt"]      # Saturday -> Friday's file expected
    kinds = [n[0] for n in ctx.st["notifications"]]
    assert kinds == ["FILE_NOT_RECEIVED"]
    assert common.owner_of(ctx) == "portfolio-data-owner"


def test_without_expectation_an_empty_drop_is_quiet():
    ctx = PipelineContext("Common", "landing", "Routine", spark=None, env=config.load_env())
    ctx.item = "file-loads/positions"
    landing_steps.read_source_yaml(ctx)
    ctx.st.update({"expect_file": False, "today": dt.date(2026, 11, 21), "all_files": [], "files": [], "good": [], "bad": [], "rows": []})
    landing_steps.validate_batch(ctx)
    assert "halt" not in ctx.st and "notifications" not in ctx.st


def test_one_table_crashing_does_not_stop_the_others(monkeypatch):
    ran = []

    class Mod:
        def __init__(self, order): self.order = order
        def run(self, ctx):
            ran.append((ctx.item, self.order))
            if ctx.item == "file-loads/positions" and self.order == 4:
                raise Exception(PATH_NOT_FOUND)

    monkeypatch.setattr(sequence, "_load", lambda path: Mod(int(path.split("/")[-1][:2])))
    ctx = PipelineContext("Common", "landing", "Routine", spark=None, env={"catalog": "edap"})
    logs = []
    with pytest.raises(common.PipelineFailure) as e:
        sequence.run_sequence(ctx, out=logs.append)
    assert "file_positions step 04 acquire_data" in str(e.value) and "PathNotFound" in str(e.value)
    assert max(o for i, o in ran if i == "file-loads/positions") == 4                       # stopped at the crash
    for item in ("sql-loads/instruments", "sql-loads/trades", "stream-loads/trade_events", "api-loads/fx_rates"):
        assert max(o for i, o in ran if i == item) == 9, item                              # every other table ran to the end
    assert any("Traceback" in l for l in logs)                                             # the full trace is in the job log


def test_halt_and_crash_in_the_same_layer_are_both_reported(monkeypatch):
    class Mod:
        def __init__(self, order): self.order = order
        def run(self, ctx):
            if ctx.item == "sql-loads/trades" and self.order == 3:
                raise common.PipelineHalt("whole file wrong")
            if ctx.item == "api-loads/fx_rates" and self.order == 4:
                raise RuntimeError("api down")

    monkeypatch.setattr(sequence, "_load", lambda path: Mod(int(path.split("/")[-1][:2])))
    ctx = PipelineContext("Common", "landing", "Routine", spark=None, env={"catalog": "edap"})
    with pytest.raises(common.PipelineFailure) as e:
        sequence.run_sequence(ctx, out=lambda *_: None)
    assert "api down" in str(e.value) and "also halted" in str(e.value) and "sql_trades" in str(e.value)


def test_event_row_count_tolerates_missing_and_none_progress():
    from edap_framework.ingestion.streaming.eventhub_to_landing import rows_read
    assert rows_read([{"numInputRows": None}, {"numInputRows": 5}, {}, None, {"numInputRows": 7}]) == 12
    assert rows_read([]) == 0 and rows_read([{}]) == 0          # the failure on the first real run: nothing new in the hub
