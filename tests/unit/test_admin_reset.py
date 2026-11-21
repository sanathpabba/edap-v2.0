import pytest

from edap_framework.admin import reset

ENV = {"catalog": "edap", "storage": {"account": "edapdl", "containers": {"landing": "landing", "bronze": "bronze"}, "uri_template": "abfss://{container}@{account}.dfs.core.windows.net/{path}"}}

# what information_schema returns: pipeline tables, plus things that must survive
ROWS = [("bronze", "equities_sql_trades", "MANAGED"), ("silver", "common_portfolio", "MANAGED"), ("gold", "fx_trade_analytics", "MANAGED"),
        ("consumption", "fx_trade_metrics", "VIEW"), ("consumption", "fx_trade_daily_mv", "MATERIALIZED_VIEW"), ("quarantine", "bronze_invalid", "MANAGED"),
        ("monitoring", "dq_results", "MANAGED"), ("monitoring", "some_other_table", "MANAGED"), ("audit", "ingestion_runs", "MANAGED"), ("audit", "file_arrivals", "MANAGED"),
        ("metadata", "watermarks", "MANAGED"), ("metadata", "other_metadata", "MANAGED"),
        ("reference", "currency", "MANAGED"), ("governance", "mask_lei", "MANAGED")]


class Row(dict):
    pass


class FakeSpark:
    def __init__(self, fail=()):
        self.statements, self.fail = [], fail

    def sql(self, q):
        if "information_schema" in q:
            schemas = set(x.strip("'") for x in q.split("IN (")[1].rstrip(")").split(","))
            class R:
                def collect(self_inner):
                    return [Row(table_schema=s, table_name=n, table_type=t) for s, n, t in ROWS if s in schemas]
            return R()
        self.statements.append(q)
        if any(f in q for f in self.fail):
            raise Exception("permission denied")


class FakeFs:
    def __init__(self, missing=()):
        self.removed, self.missing = [], missing

    def rm(self, uri, recursive):
        if any(m in uri for m in self.missing):
            raise Exception("java.io.FileNotFoundException: PathNotFound")
        self.removed.append(uri)


class FakeDbutils:
    def __init__(self, **kw): self.fs = FakeFs(**kw)


def test_plan_targets_only_pipeline_objects_and_keeps_reference_and_governance():
    names = {fq for _, fq in reset.plan(FakeSpark(), ENV)["drop"]}
    assert "edap.bronze.equities_sql_trades" in names and "edap.silver.common_portfolio" in names and "edap.quarantine.bronze_invalid" in names
    assert {"edap.monitoring.dq_results", "edap.audit.ingestion_runs", "edap.audit.file_arrivals", "edap.metadata.watermarks"} <= names
    assert not any(".reference." in n or ".governance." in n or "some_other_table" in n or "other_metadata" in n for n in names)


def test_views_and_materialized_views_get_the_right_drop_statement():
    stm = dict((fq, s) for s, fq in reset.plan(FakeSpark(), ENV)["drop"])
    assert stm["edap.consumption.fx_trade_metrics"].startswith("DROP VIEW") and stm["edap.consumption.fx_trade_daily_mv"].startswith("DROP MATERIALIZED VIEW")
    assert stm["edap.gold.fx_trade_analytics"].startswith("DROP TABLE")


def test_landing_and_checkpoint_folders_only_never_the_source_drop():
    deletes = reset.plan(FakeSpark(), ENV)["delete"]
    assert "abfss://landing@edapdl.dfs.core.windows.net/sql" in deletes and "abfss://bronze@edapdl.dfs.core.windows.net/_checkpoints" in deletes
    assert not any("sourcedrop" in d for d in deletes)


def test_refuses_without_confirmation_and_for_other_catalogs():
    with pytest.raises(PermissionError):
        reset.reset_platform(FakeSpark(), FakeDbutils(), ENV, log=lambda *_: None)
    with pytest.raises(ValueError, match="only the 'edap' catalog"):
        reset.plan(FakeSpark(), {**ENV, "catalog": "edap_prod"})


def test_dry_run_changes_nothing():
    s, d = FakeSpark(), FakeDbutils()
    out = reset.reset_platform(s, d, ENV, dry_run=True, log=lambda *_: None)
    assert out["executed"] is False and s.statements == [] and d.fs.removed == []


def test_confirmed_reset_executes_and_reports_failures_without_stopping():
    s, d = FakeSpark(fail=("silver.common_portfolio",)), FakeDbutils(missing=("_checkpoints",))
    out = reset.reset_platform(s, d, ENV, confirm=True, log=lambda *_: None)
    assert out["executed"] and out["dropped"] == len(out["drop"]) - 1 and len(out["failed"]) == 1 and "common_portfolio" in out["failed"][0]
    assert len(s.statements) == len(out["drop"]) and len(d.fs.removed) == 4         # the two missing _checkpoints folders count as already clean
