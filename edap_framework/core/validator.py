"""Offline definition validator (no Spark needed): checks every YAML in definitions/ against the others.
Catches broken references before a run: missing files, unknown tables, rule columns that do not exist, bad dependencies."""
import os
import re

from edap_framework.core import config

KNOWN_DQX = {"is_not_null", "is_not_empty", "is_not_null_and_not_empty", "is_in_list", "is_not_in_list", "regex_match", "is_unique",
             "sql_expression", "is_in_range", "is_not_less_than", "is_not_greater_than", "is_valid_date", "is_valid_timestamp"}
SQL_WORDS = set("""and or not null is in between like case when then else end as true false select from where cast try_cast abs round
coalesce nullif concat concat_ws substr trim upper lower try_to_date try_to_timestamp current_date current_timestamp datediff sum count
max min over partition by order desc asc rows unbounded preceding current row last_value to_date to_timestamp date timestamp string int
double decimal boolean interval day sequence explode distinct group join on left right cross left inner expr uuid sha2 regexp_extract""".split())


def _files(layer):
    d = os.path.join(config.project_root(), "definitions", layer)
    out = []
    for root, _, fs in os.walk(d):
        out += [os.path.relpath(os.path.join(root, f), config.project_root()) for f in fs if f.endswith(".yml")]
    return sorted(out)


def _idents(expr):
    expr = re.sub(r"'[^']*'", "''", expr)
    toks = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b(?!\s*\()", expr)
    return {t for t in toks if t.lower() not in SQL_WORDS and not re.match(r"^[a-z]$", t)}


def rule_columns(rule_set):
    cols = set()
    for c in rule_set["checks"]:
        a = c["check"].get("arguments", {})
        if "column" in a:
            cols.add(a["column"])
        cols |= set(a.get("columns", []))
        if c["check"]["function"] == "sql_expression":
            cols |= _idents(a["expression"])
    return cols


TYPE_RX = re.compile(r"^(string|int|bigint|long|double|float|boolean|date|timestamp|decimal\(\d+,\d+\))$")


def _check_columns(where, columns, err):
    """Column names must be identifiers and types valid Spark types (catches e.g. an unquoted decimal(18,6) split by YAML)."""
    for c, t in columns.items():
        if not isinstance(c, str) or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", c):
            err("%s: malformed column name %r" % (where, c))
        if not isinstance(t, str) or not TYPE_RX.match(t):
            err("%s: column %s has malformed type %r" % (where, c, t))


def validate():
    errors, warns = [], []
    err = errors.append
    for f in _files(""):
        try:
            config.load_yaml(f)
        except Exception as e:                                       # noqa: BLE001
            err("%s: does not parse (%s)" % (f, e))
    exists = lambda rel: os.path.exists(os.path.join(config.project_root(), rel))

    # ---- sources
    src = config.load_yaml("definitions/sources/azure_sql_trading.yml")
    for o in src["objects"]:
        if o.get("columns"):
            _check_columns("sources/azure_sql_trading.yml:" + o["name"], o["columns"], err)
    src_cols = {o["name"]: set(o["columns"]) for o in src["objects"] if o.get("ingest", True) is not False and "columns" in o}

    # ---- landing
    for f in _files("landing"):
        s = config.load_yaml(f)
        if s.get("source_definition") and not exists(s["source_definition"]):
            err("%s: source_definition %s missing" % (f, s["source_definition"]))
        if "sql-loads" in f:
            cols = set(s["extract"]["columns"])
            if s["source_object"] not in src_cols:
                err("%s: source_object %s not in source contract" % (f, s["source_object"]))
            elif not cols <= src_cols[s["source_object"]]:
                err("%s: columns not in source contract: %s" % (f, sorted(cols - src_cols[s["source_object"]])))
            if s["extract"]["watermark_column"] not in cols:
                err("%s: watermark column not extracted" % f)

    # ---- bronze
    bronze_targets, bronze_cols, seen_cp = {}, {}, {}
    for f in _files("bronze"):
        s = config.load_yaml(f)
        fq = "%s.%s.%s" % (s["target"]["catalog"], s["target"]["schema"], s["target"]["table"])
        if fq in bronze_targets:
            err("%s: target %s also used by %s" % (f, fq, bronze_targets[fq]))
        bronze_targets[fq] = f
        for key in ("columns",):
            if s.get(key):
                _check_columns(f, s[key], err)
        if (s.get("parse") or {}).get("columns"):
            _check_columns(f + ":parse", s["parse"]["columns"], err)
        cp = s["checkpoint"]["path"]
        if cp in seen_cp:
            err("%s: checkpoint %s shared with %s" % (f, cp, seen_cp[cp]))
        seen_cp[cp] = f
        if not exists(s["input"]["landing_spec"]):
            err("%s: landing_spec %s missing" % (f, s["input"]["landing_spec"]))
        for blk in ("lineage", "governance", "audit_columns"):
            if blk not in s:
                err("%s: missing block %s" % (f, blk))
        cols = set(s.get("columns", {})) | set((s.get("parse") or {}).get("columns", {})) | set(s.get("json_extract", {})) | set(s.get("extra_columns", {})) \
            | set((s.get("parse") or {}) and s["transport_columns"]) | {s.get("raw_column")} - {None}
        cols |= {"_source_system", "_source_object", "_batch_id", "_ingest_ts", "_ingest_date", "_source_file", "_row_hash", "_landing_batch_id"}
        bronze_cols[fq] = cols
        if "sql-loads" in f and "columns" in s:
            lp = config.load_yaml(s["input"]["landing_spec"])
            if set(s["columns"]) != set(lp["extract"]["columns"]):
                err("%s: Bronze columns differ from the landing extract columns" % f)
        rf = s.get("dq", {}).get("rules_file")
        if rf and not exists(rf):
            err("%s: dq rules_file %s missing" % (f, rf))

    # ---- silver mappings
    ent = {}
    for f in _files("mappings"):
        m = config.load_yaml(f); ent[m["entity"]] = (f, m)
    silver_targets = {"edap.silver.%s" % e: m for e, (f, m) in ent.items()}
    ref_targets = {"edap.reference.%s" % os.path.basename(f)[:-4] for f in _files("reference_data")}
    silver_cols = {}
    for e, (f, m) in ent.items():
        if m["source"]["bronze_table"] not in bronze_targets:
            err("%s: bronze_table %s is not produced by any Bronze spec" % (f, m["source"]["bronze_table"]))
        for d in m.get("depends_on", []):
            if d != "reference" and d not in ent:
                err("%s: depends_on %s is not an entity" % (f, d))
        cols = set(m["columns"])
        for lk in m.get("lookups", []):
            if lk["table"] not in silver_targets and lk["table"] not in ref_targets:
                err("%s: lookup table %s unknown" % (f, lk["table"]))
            if lk["table"].startswith("edap.silver.") and lk["table"].split(".")[-1] not in m.get("depends_on", []):
                err("%s: lookup on %s but it is not in depends_on" % (f, lk["table"]))
            for dc in lk["on"]:
                if dc not in cols:
                    err("%s: lookup join column %s not a mapped column" % (f, dc))
            cols |= set(lk.get("add", {})) | ({lk["flag"]} if "flag" in lk else set())
        for k in m["business_key"] + m["merge"]["keys"]:
            if k not in cols:
                err("%s: key %s not in columns" % (f, k))
        for o in m["dedup"]["order_by"] + [m["dedup"]["partition_by"]][0]:
            if not _idents(o) <= (cols | {"_ingest_ts"}):
                err("%s: dedup refers to unknown column(s) %s" % (f, sorted(_idents(o) - cols - {"_ingest_ts"})))
        silver_cols[e] = cols
        rf = m.get("dq", {}).get("rules_file")
        if not rf or not exists(rf):
            err("%s: dq rules_file missing" % f)
        else:
            rs = config.load_yaml(rf)
            if rs["target_table"] != "edap.silver.%s" % e:
                err("%s: target_table %s does not match entity" % (rf, rs["target_table"]))
            miss = rule_columns(rs) - cols
            if miss:
                err("%s: rules refer to columns not produced by the mapping: %s" % (rf, sorted(miss)))

    # ---- bronze rules vs bronze columns
    for f in _files("dq_rules/bronze"):
        rs = config.load_yaml(f)
        if rs["target_table"] not in bronze_targets:
            err("%s: target_table %s is not a Bronze table" % (f, rs["target_table"]))
        else:
            miss = rule_columns(rs) - bronze_cols[rs["target_table"]]
            if miss:
                err("%s: rules refer to columns not in Bronze: %s" % (f, sorted(miss)))
    for f in _files("dq_rules"):
        for c in config.load_yaml(f)["checks"]:
            if c["check"]["function"] not in KNOWN_DQX:
                err("%s: unknown DQX function %s" % (f, c["check"]["function"]))
            if not c.get("name"):
                warns.append("%s: a %s check has no name" % (f, c["check"]["function"]))

    # ---- gold
    gold_targets, gold_cols = {}, {}
    for f in _files("gold_products"):
        p = config.load_yaml(f)
        gold_targets["edap.gold.%s" % p["product"]] = f
        gold_cols["edap.gold.%s" % p["product"]] = set(p["select"].get("dimensions", {})) | set(p["select"].get("measures", {}))
    for t, f in gold_targets.items():
        p = config.load_yaml(f)
        ctes = {c["name"] for c in p.get("with", [])}
        refs = {p["from"]["table"]} | {j["table"] for j in p.get("joins", [])}
        for c in p.get("with", []):
            refs |= set(re.findall(r"\b(edap\.[a-z_]+\.[a-z_]+)\b", c["sql"]))
        for r in refs:
            if r in ctes:
                continue
            if r not in silver_targets and r not in gold_targets and r not in ref_targets:
                err("%s: references unknown table %s" % (f, r))
        rf = p.get("dq", {}).get("rules_file")
        if rf:
            if not exists(rf):
                err("%s: dq rules_file missing" % f)
            else:
                miss = rule_columns(config.load_yaml(rf)) - gold_cols[t]
                if miss:
                    err("%s: rules refer to columns not in the product: %s" % (rf, sorted(miss)))
        for k in ("business_purpose", "grain", "owner", "refresh_pattern", "intended_consumers"):
            if k not in p["documentation"]:
                err("%s: documentation.%s missing" % (f, k))

    # ---- governance
    acc = config.load_yaml("definitions/governance/access.yml")
    for g in acc["grants"]:
        if g["on"]["type"] == "TABLE" and g["on"]["name"] not in gold_targets and g["on"]["name"] not in silver_targets:
            err("access.yml: grant on unknown table %s" % g["on"]["name"])
        if g["principal"] not in acc["groups"]:
            err("access.yml: principal %s not declared in groups" % g["principal"])
    for mk in config.load_yaml("definitions/governance/masking.yml")["masks"]:
        t = mk["table"]
        if t not in silver_targets or mk["column"] not in silver_cols[t.split(".")[-1]]:
            err("masking.yml: %s.%s does not exist" % (t, mk["column"]))
    lin = config.load_yaml("definitions/governance/lineage.yml")
    for p in lin["products"]:
        if p not in gold_targets:
            err("lineage.yml: product %s unknown" % p)
    return errors, warns
