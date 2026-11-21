"""Gold building blocks (each is called by one pipeline step; see pipelines/*/gold/*/NN_*.py):
read product YAML -> resolve parameters -> check upstream -> compose_sql -> write_product -> document -> expectations."""
import re

from edap_framework.core import spark_utils
from edap_framework.dq.engine import apply_rule_set, load_rule_set


def _sub(text, params):
    for k, v in params.items():
        text = text.replace("${%s}" % k, str(v))
    return text


def resolve_parameters(product, overrides=None):
    """Product parameters from YAML, overridden by run parameters (Adhoc what-if runs). Returns the merged dict."""
    return {**product.get("parameters", {}), **(overrides or {})}


def upstream_tables(product):
    """Every UC table the product reads (base table, joins and tables named inside CTEs), minus its own CTE names."""
    ctes = {c["name"] for c in product.get("with", [])}
    refs = {product["from"]["table"]} | {j["table"] for j in product.get("joins", [])}
    for c in product.get("with", []):
        refs |= set(re.findall(r"\b(edap\.[a-z_]+\.[a-z_]+)\b", c["sql"]))
    return sorted(r for r in refs if r not in ctes)


def check_upstream(spark, product):
    """Fail early (clear message) when an upstream table is missing or empty."""
    missing = [t for t in upstream_tables(product) if not spark.catalog.tableExists(t)]
    empty = [t for t in upstream_tables(product) if t not in missing and spark.table(t).limit(1).count() == 0]
    if missing or empty:
        raise RuntimeError("Gold %s blocked: missing %s, empty %s" % (product["product"], missing, empty))


def compose_sql(p, params=None):
    params = params if params is not None else p.get("parameters", {})
    sub = lambda s: _sub(s, params)
    parts = []
    if p.get("with"):
        parts.append("WITH " + ",\n".join("%s AS (%s)" % (c["name"], sub(c["sql"])) for c in p["with"]))
    sel = ["%s AS %s" % (sub(expr), name) for section in ("dimensions", "measures") for name, expr in (p["select"].get(section) or {}).items()]
    base = p["from"]
    sql = "SELECT\n  " + ",\n  ".join(sel) + "\nFROM %s %s" % (base["table"], base["alias"])
    for j in p.get("joins", []):
        on = "" if j["type"].lower() == "cross" else " ON " + sub(j["on"])
        sql += "\n%s JOIN %s %s%s" % (j["type"].upper(), j["table"], j["alias"], on)
    if p.get("where"):
        sql += "\nWHERE " + sub(p["where"])
    if p.get("group_by"):
        sql += "\nGROUP BY " + ", ".join(p["group_by"])
    return ("\n".join(parts) + "\n" if parts else "") + sql


def write_product(spark, sql, product):
    fq = spark_utils.fq_table(product["target"])
    spark.sql("CREATE SCHEMA IF NOT EXISTS %s.%s" % (product["target"]["catalog"], product["target"]["schema"]))
    spark.sql(sql).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(fq)
    return spark.table(fq).count()


def document(spark, product, spec_path, asset_class):
    fq, d = spark_utils.fq_table(product["target"]), product["documentation"]
    esc = lambda s: str(s).replace("'", "''")
    spark.sql("COMMENT ON TABLE %s IS '%s'" % (fq, esc("%s | Asset class: %s | Grain: %s | Refresh: %s | Consumers: %s" % (
        d["business_purpose"], asset_class, d["grain"], d["refresh_pattern"], d["intended_consumers"]))))
    tags = {"layer": "gold", "asset_class": asset_class, "data_product": product["product"], "owner": d["owner"],
            "sensitivity": d.get("sensitivity", "synthetic"), "grain": d["grain"], "refresh": d["refresh_pattern"], "spec": spec_path}
    spark.sql("ALTER TABLE %s SET TAGS (%s)" % (fq, ", ".join("'%s' = '%s'" % (k, esc(v)) for k, v in tags.items())))
    for col, text in (product.get("column_comments") or {}).items():
        spark.sql("ALTER TABLE %s ALTER COLUMN %s COMMENT '%s'" % (fq, col, esc(text)))


def run_expectations(spark, product, env, batch_id, rules_vars):
    rf = product.get("dq", {}).get("rules_file")
    if not rf:
        return None
    fq = spark_utils.fq_table(product["target"])
    return apply_rule_set(spark, spark.table(fq), load_rule_set(rf, rules_vars), env, batch_id, table_name=fq)[1]
