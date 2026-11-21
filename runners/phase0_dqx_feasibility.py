# Databricks notebook source
# Phase 0 / FND-10: DQX feasibility + secret-scope check (no business data)
import yaml
from databricks.sdk import WorkspaceClient
from databricks.labs.dqx.engine import DQEngine
import importlib.metadata as md

print("dqx version:", md.version("databricks-labs-dqx"))

# secret scope check (print length only, never the value)
v = dbutils.secrets.get("edap-kv", "sql-server-name")
print("secret scope OK, sql-server-name length:", len(v))

rules_yaml = """
- criticality: error
  check:
    function: is_not_null
    arguments: {column: trade_id}
- criticality: error
  name: currency_approved
  check:
    function: sql_expression
    arguments:
      expression: "currency IN ('USD','EUR','GBP')"
      msg: currency not in approved list
- criticality: warn
  check:
    function: is_unique
    arguments: {columns: [trade_id]}
"""
checks = yaml.safe_load(rules_yaml)

df = spark.createDataFrame(
    [("TRD0000001", "USD"), ("TRD0000002", "EUR"), (None, "USD"), ("TRD0000004", "XXX"), ("TRD0000001", "GBP")],
    "trade_id string, currency string")

dq = DQEngine(WorkspaceClient())
valid, quarantined = dq.apply_checks_by_metadata_and_split(df, checks)
print("input rows:", df.count(), "valid:", valid.count(), "quarantined:", quarantined.count())
quarantined.show(truncate=False)
result = {"dqx_version": md.version("databricks-labs-dqx"), "secret_len": len(v), "input": df.count(), "valid": valid.count(), "quarantined": quarantined.count(), "reasons": [r["_errors"] and [e["name"] for e in r["_errors"]] for r in quarantined.collect()] if "_errors" in quarantined.columns else None}

# also test is_in_list with quoted literals (this DQX version treats bare strings as column names)
try:
    alt = yaml.safe_load("""
- criticality: error
  check:
    function: is_in_list
    arguments: {column: currency, allowed: ["'USD'", "'EUR'", "'GBP'"]}
""")
    v2, q2 = dq.apply_checks_by_metadata_and_split(df, alt)
    print("is_in_list quoted literals OK: valid", v2.count(), "quarantined", q2.count())
    result["is_in_list_quoted"] = [v2.count(), q2.count()]
except Exception as e:
    print("is_in_list quoted literals FAILED:", str(e)[:200])
    result["is_in_list_quoted"] = "FAILED: " + str(e)[:150]

import json
dbutils.notebook.exit(json.dumps(result, default=str))
