"""Gold product builder. One call = one product (definitions/gold_products/<product>.yml).
The YAML holds the whole product: documentation (purpose, grain, owner, refresh, consumers), optional CTEs, base table,
joins, dimensions/measures and parameters. The builder composes the SQL, writes the Delta table, applies the documentation
as Unity Catalog comments/tags, and runs the product's DQX expectations in flag mode."""
import datetime as dt

from edap_framework.core import audit, spark_utils
from edap_framework.dq.engine import apply_rule_set, load_rule_set


def compose_sql(p):
    params = p.get("parameters", {})
    sub = lambda s: _sub(s, params)
    parts = []
    if p.get("with"):
        parts.append("WITH " + ",\n".join("%s AS (%s)" % (c["name"], sub(c["sql"])) for c in p["with"]))
    sel = []
    for section in ("dimensions", "measures"):
        for name, expr in (p["select"].get(section) or {}).items():
            sel.append("%s AS %s" % (sub(expr), name))
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


def _sub(text, params):
    for k, v in params.items():
        text = text.replace("${%s}" % k, str(v))
    return text


def build_product(spark, product, env, batch_id=None, scenario=None, spec_path=None):
    batch_id = batch_id or audit.new_batch_id()
    spec_path = spec_path or "definitions/gold_products/%s.yml" % product["product"]
    started = dt.datetime.utcnow()
    tgt = product["target"]
    fq = spark_utils.fq_table(tgt)
    spark.sql("CREATE SCHEMA IF NOT EXISTS %s.%s" % (tgt["catalog"], tgt["schema"]))
    sql = compose_sql(product)
    df = spark.sql(sql)
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(fq)
    n = spark.table(fq).count()
    _document(spark, fq, product, spec_path)
    stats = None
    if product.get("dq", {}).get("rules_file"):
        _, stats = apply_rule_set(spark, spark.table(fq), load_rule_set(product["dq"]["rules_file"]), env, batch_id, table_name=fq)
    audit.log_run(spark, "%s.audit.ingestion_runs" % env["catalog"], batch_id=batch_id, layer="gold", source_system="EDAP", table_name=product["product"],
                  scenario=scenario, status="SUCCESS", rows_processed=n, started_ts=started, finished_ts=dt.datetime.utcnow(),
                  details="%s; dq %s" % (fq, stats))
    return {"rows": n, "dq": stats}


def _document(spark, fq, product, spec_path):
    d = product["documentation"]
    esc = lambda s: str(s).replace("'", "''")
    comment = "%s | Grain: %s | Refresh: %s | Consumers: %s" % (d["business_purpose"], d["grain"], d["refresh_pattern"], d["intended_consumers"])
    spark.sql("COMMENT ON TABLE %s IS '%s'" % (fq, esc(comment)))
    tags = {"layer": "gold", "data_product": product["product"], "owner": d["owner"], "sensitivity": d.get("sensitivity", "synthetic"),
            "grain": d["grain"], "refresh": d["refresh_pattern"], "spec": spec_path}
    spark.sql("ALTER TABLE %s SET TAGS (%s)" % (fq, ", ".join("'%s' = '%s'" % (k, esc(v)) for k, v in tags.items())))
    for col, text in (product.get("column_comments") or {}).items():
        spark.sql("ALTER TABLE %s ALTER COLUMN %s COMMENT '%s'" % (fq, col, esc(text)))
