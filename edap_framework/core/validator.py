"""Offline definition validator (no Spark needed). Expands every definition per asset class exactly as the pipelines load it, then checks
the cross-references: files, tables, rule columns, dependencies, routing coverage, and the pipelines/ step files themselves."""
import ast
import os
import re

from edap_framework.core import config

KNOWN_DQX = {"is_not_null", "is_not_empty", "is_not_null_and_not_empty", "is_in_list", "is_not_in_list", "regex_match", "is_unique",
             "sql_expression", "is_in_range", "is_not_less_than", "is_not_greater_than", "is_valid_date", "is_valid_timestamp"}
SQL_WORDS = set("""and or not null is in between like case when then else end as true false select from where cast try_cast abs round
coalesce nullif concat concat_ws substr trim upper lower try_to_date try_to_timestamp current_date current_timestamp datediff sum count
max min over partition by order desc asc rows unbounded preceding current row last_value to_date to_timestamp date timestamp string int
double decimal boolean interval day sequence explode distinct group join on left right cross inner expr uuid sha2 regexp_extract""".split())
TYPE_RX = re.compile(r"^(string|int|bigint|long|double|float|boolean|date|timestamp|decimal\(\d+,\d+\))$")
LAYERS = ["landing", "bronze", "silver", "gold"]


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


def _check_columns(where, columns, err):
    for c, t in columns.items():
        if not isinstance(c, str) or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", c):
            err("%s: malformed column name %r" % (where, c))
        if not isinstance(t, str) or not TYPE_RX.match(t):
            err("%s: column %s has malformed type %r" % (where, c, t))


def _yaml_files():
    base = os.path.join(config.project_root(), "definitions")
    return sorted(os.path.relpath(os.path.join(r, f), config.project_root()) for r, _, fs in os.walk(base) for f in fs if f.endswith(".yml"))


def _step_functions(layer):
    """Function names defined (or aliased) in edap_framework/pipeline/<layer>_steps.py, read with ast (no imports)."""
    path = os.path.join(config.project_root(), "edap_framework", "pipeline", "%s_steps.py" % layer)
    tree = ast.parse(open(path).read())
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    names |= {t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    return names


def _step_call(path):
    m = re.search(r"steps\.(\w+)\(ctx\)", open(path).read())
    return m.group(1) if m else None


def validate():
    errors, warns = [], []
    err = errors.append
    exists = lambda rel: os.path.exists(os.path.join(config.project_root(), rel))
    acs = config.list_asset_classes()
    by_prefix = {a.prefix: a for a in acs}
    dummy = acs[0].variables()

    for f in _yaml_files():                                         # every file must parse (templates filled with a dummy asset class)
        try:
            config.load_yaml(f, dummy)
        except Exception as e:                                       # noqa: BLE001
            err("%s: does not parse (%s)" % (f, e))

    # ---- asset classes
    if sum(1 for a in acs if a.receives_unresolved) != 1:
        err("asset_classes: exactly one pipeline must have receives_unresolved: true")
    seen_types = {}
    for a in acs:
        for t in a.sec_types:
            if t in seen_types:
                err("asset_classes: sec_type %s routed to both %s and %s" % (t, seen_types[t], a.folder))
            seen_types[t] = a.folder
        for layer, items in a.items.items():
            if layer not in LAYERS:
                err("asset_classes/%s: unknown layer %s" % (a.folder, layer))
    src = config.load_yaml("definitions/sources/azure_sql_trading.yml")
    for o in src["objects"]:
        if o.get("columns"):
            _check_columns("sources/azure_sql_trading.yml:" + o["name"], o["columns"], err)
    src_cols = {o["name"]: set(o["columns"]) for o in src["objects"] if o.get("ingest", True) is not False and "columns" in o}

    # ---- pipelines folder tree: pipelines/<AssetClass>/<layer>/<table>/<Routine|Adhoc>/NN_<step>.py
    root = config.project_root()
    for a in acs:
        for layer, items in a.items.items():
            if layer in LAYERS:
                folders = [config.table_folder(layer, i) for i in items]
                if len(set(folders)) != len(folders):
                    err("asset_classes/%s: %s items map to duplicate table folders" % (a.folder, layer))
            fns = _step_functions(layer) if layer in LAYERS else set()
            layer_dir = os.path.join(root, "pipelines", a.folder, layer)
            expected = {config.table_folder(layer, i): i for i in items}
            actual = set(os.listdir(layer_dir)) - {"__pycache__"} if os.path.isdir(layer_dir) else set()
            for orphan in sorted(actual - set(expected)):
                err("pipelines/%s/%s/%s: table folder is not listed in definitions/asset_classes/%s.yml" % (a.folder, layer, orphan, a.prefix))
            for folder, item in expected.items():
                seqs = {}
                for mode in ("Routine", "Adhoc"):
                    d = os.path.join(layer_dir, folder, mode)
                    where = "pipelines/%s/%s/%s/%s" % (a.folder, layer, folder, mode)
                    if not os.path.isdir(d):
                        err("%s missing" % where); continue
                    files = sorted(f for f in os.listdir(d) if re.match(r"^\d{2}_[a-z0-9_]+\.py$", f))
                    nums = [int(f[:2]) for f in files]
                    if nums != list(range(1, len(nums) + 1)) or not 8 <= len(nums) <= 10:
                        err("%s: steps must be 01..NN with 8-10 files, found %s" % (where, nums))
                    calls = []
                    for f in files:
                        text = open(os.path.join(d, f)).read()
                        call = _step_call(os.path.join(d, f))
                        calls.append(call)
                        m = re.search(r'^ITEM = "([^"]+)"', text, re.M)
                        if not m or m.group(1) != item:
                            err("%s/%s: ITEM must be %r" % (where, f, item))
                        if call is None or call not in fns:
                            err("%s/%s: calls %s which is not in %s_steps.py" % (where, f, call, layer))
                        elif f[3:-3] != call:
                            err("%s/%s: file name does not match function %s" % (where, f, call))
                    seqs[mode] = calls
                if len(seqs) == 2 and seqs["Routine"] != seqs["Adhoc"]:
                    err("pipelines/%s/%s/%s: Routine and Adhoc step sequences differ" % (a.folder, layer, folder))

    # ---- landing items
    for a in acs:
        for item in a.items.get("landing", []):
            f = "definitions/landing/%s.yml" % item
            if not exists(f):
                err("%s: landing item %s has no spec" % (a.folder, item)); continue
            s = config.load_yaml(f, a.variables())
            if s.get("source_definition") and not exists(s["source_definition"]):
                err("%s: source_definition %s missing" % (f, s["source_definition"]))
            if item.startswith("sql-loads/"):
                cols = set(s["extract"]["columns"])
                if s["source_object"] not in src_cols:
                    err("%s: source_object %s not in source contract" % (f, s["source_object"]))
                elif not cols <= src_cols[s["source_object"]]:
                    err("%s: columns not in source contract: %s" % (f, sorted(cols - src_cols[s["source_object"]])))
                if s["extract"]["watermark_column"] not in cols:
                    err("%s: watermark column not extracted" % f)
    landing_items = {i for a in acs for i in a.items.get("landing", [])}

    # ---- bronze
    bronze_targets, bronze_cols, seen_cp = {}, {}, {}
    for a in acs:
        for item in a.items.get("bronze", []):
            f = "definitions/bronze/%s.yml" % item
            if not exists(f):
                err("%s: bronze item %s has no spec" % (a.folder, item)); continue
            s = config.load_yaml(f, a.variables())
            fq = "%s.%s.%s" % (s["target"]["catalog"], s["target"]["schema"], s["target"]["table"])
            if fq in bronze_targets:
                err("%s: target %s also produced by %s" % (f, fq, bronze_targets[fq]))
            bronze_targets[fq] = "%s:%s" % (a.folder, item)
            cp = s["checkpoint"]["path"]
            if cp in seen_cp:
                err("%s: checkpoint %s shared with %s" % (f, cp, seen_cp[cp]))
            seen_cp[cp] = f
            if item not in landing_items:
                err("%s: bronze item %s has no landing item in any pipeline" % (a.folder, item))
            if not exists(s["input"]["landing_spec"]):
                err("%s: landing_spec %s missing" % (f, s["input"]["landing_spec"]))
            for blk in ("lineage", "governance", "audit_columns", "scope"):
                if blk not in s:
                    err("%s: missing block %s" % (f, blk))
            sc = s.get("scope", {})
            if sc.get("by") == "instrument" and (not sc.get("column") or not a.sec_types):
                err("%s: instrument routing needs a column and an asset class with sec_types (not Common)" % f)
            if s.get("columns"):
                _check_columns(f, s["columns"], err)
            if (s.get("parse") or {}).get("columns"):
                _check_columns(f + ":parse", s["parse"]["columns"], err)
            cols = set(s.get("columns", {})) | set((s.get("parse") or {}).get("columns", {})) | set(s.get("json_extract", {})) | set(s.get("extra_columns", {}))
            cols |= set(s.get("transport_columns", {})) | ({s["raw_column"]} if s.get("raw_column") else set())
            cols |= {"_source_system", "_source_object", "_batch_id", "_ingest_ts", "_ingest_date", "_source_file", "_row_hash", "_landing_batch_id"}
            bronze_cols[fq] = cols
            if item.startswith("sql-loads/"):
                lp = config.load_yaml(s["input"]["landing_spec"], a.variables())
                if set(s["columns"]) != set(lp["extract"]["columns"]):
                    err("%s: Bronze columns differ from the landing extract columns" % f)
            rf = s.get("dq", {}).get("rules_file")
            if not rf or not exists(rf):
                err("%s: dq rules_file %s missing" % (f, rf))
            else:
                rs = config.load_yaml(rf, a.variables())
                if rs["target_table"] != fq:
                    err("%s: target_table %s != %s" % (rf, rs["target_table"], fq))
                miss = rule_columns(rs) - cols
                if miss:
                    err("%s (%s): rules refer to columns not in Bronze: %s" % (rf, a.folder, sorted(miss)))
                for c in rs["checks"]:
                    if c["check"]["function"] not in KNOWN_DQX:
                        err("%s: unknown DQX function %s" % (rf, c["check"]["function"]))
                    if not c.get("name"):
                        warns.append("%s: a %s check has no name" % (rf, c["check"]["function"]))

    # ---- routing coverage: every allowed sec_type is routed somewhere
    allowed = None
    for c in config.load_yaml("definitions/dq_rules/bronze/sql_instruments.yml", dummy)["checks"]:
        if c["name"] == "sec_type_allowed":
            allowed = {x.strip("'") for x in c["check"]["arguments"]["allowed"]}
    if allowed is not None and allowed != set(seen_types):
        err("routing: sec_types allowed by DQ %s != routed by asset classes %s" % (sorted(allowed), sorted(seen_types)))

    # ---- silver
    silver_targets, silver_cols, silver_order = {}, {}, {}
    ref_targets = {"edap.reference.%s" % os.path.basename(f)[:-4] for f in _yaml_files() if "/reference_data/" in f}
    for a in acs:                                                    # first pass: every produced table
        for item in a.items.get("silver", []):
            if exists("definitions/mappings/%s.yml" % item):
                m = config.load_yaml("definitions/mappings/%s.yml" % item, a.variables())
                silver_targets["edap.silver.%s" % m["target"]["table"]] = (a.folder, item)
    for a in acs:
        done_here = set()
        for item in a.items.get("silver", []):
            f = "definitions/mappings/%s.yml" % item
            if not exists(f):
                err("%s: silver item %s has no mapping" % (a.folder, item)); continue
            m = config.load_yaml(f, a.variables())
            fq = "edap.silver.%s" % m["target"]["table"]
            if m["source"]["bronze_table"] not in bronze_targets:
                err("%s (%s): bronze_table %s is not produced by any Bronze spec" % (f, a.folder, m["source"]["bronze_table"]))
            cols = set(m["columns"])
            for lk in m.get("lookups", []):
                t = lk["table"]
                if t not in silver_targets and t not in ref_targets:
                    err("%s (%s): lookup table %s unknown" % (f, a.folder, t))
                if t in silver_targets:
                    owner_pipeline, owner_item = silver_targets[t]
                    if owner_pipeline != "Common" and not (owner_pipeline == a.folder and owner_item in done_here):
                        err("%s (%s): lookup %s is built later or by another asset class" % (f, a.folder, t))
                for dc in lk["on"]:
                    if dc not in cols:
                        err("%s: lookup join column %s not a mapped column" % (f, dc))
                cols |= set(lk.get("add", {})) | ({lk["flag"]} if "flag" in lk else set())
            for k in m["business_key"] + m["merge"]["keys"]:
                if k not in cols:
                    err("%s: key %s not in columns" % (f, k))
            for o in m["dedup"]["order_by"] + m["dedup"]["partition_by"]:
                if not _idents(o) <= (cols | {"_ingest_ts"}):
                    err("%s: dedup refers to unknown column(s) %s" % (f, sorted(_idents(o) - cols - {"_ingest_ts"})))
            silver_cols[fq] = cols
            rf = m.get("dq", {}).get("rules_file")
            if not rf or not exists(rf):
                err("%s: dq rules_file missing" % f)
            else:
                rs = config.load_yaml(rf, a.variables())
                if rs["target_table"] != fq:
                    err("%s (%s): target_table %s != %s" % (rf, a.folder, rs["target_table"], fq))
                miss = rule_columns(rs) - cols
                if miss:
                    err("%s (%s): rules refer to columns not produced by the mapping: %s" % (rf, a.folder, sorted(miss)))
                for c in rs["checks"]:
                    if c["check"]["function"] not in KNOWN_DQX:
                        err("%s: unknown DQX function %s" % (rf, c["check"]["function"]))
            done_here.add(item)

    # ---- gold
    gold_targets, gold_cols = {}, {}
    for a in acs:
        for item in a.items.get("gold", []):
            if exists("definitions/gold_products/%s.yml" % item):
                p = config.load_yaml("definitions/gold_products/%s.yml" % item, a.variables())
                fq = "edap.gold.%s" % p["target"]["table"]
                gold_targets[fq] = (a.folder, item)
                gold_cols[fq] = set(p["select"].get("dimensions", {})) | set(p["select"].get("measures", {}))
    for a in acs:
        done_here = set()
        for item in a.items.get("gold", []):
            f = "definitions/gold_products/%s.yml" % item
            if not exists(f):
                err("%s: gold item %s has no product definition" % (a.folder, item)); continue
            p = config.load_yaml(f, a.variables())
            fq = "edap.gold.%s" % p["target"]["table"]
            ctes = {c["name"] for c in p.get("with", [])}
            refs = {p["from"]["table"]} | {j["table"] for j in p.get("joins", [])}
            for c in p.get("with", []):
                refs |= set(re.findall(r"\b(edap\.[a-z_]+\.[a-z_]+)\b", c["sql"]))
            for r in refs:
                if r in ctes:
                    continue
                if r not in silver_targets and r not in gold_targets and r not in ref_targets:
                    err("%s (%s): references unknown table %s" % (f, a.folder, r))
                if r in gold_targets and gold_targets[r][0] != "Common" and not (gold_targets[r][0] == a.folder and gold_targets[r][1] in done_here):
                    err("%s (%s): reads gold table %s which is built later or elsewhere" % (f, a.folder, r))
                if r in silver_targets and silver_targets[r][0] not in ("Common", a.folder):
                    err("%s (%s): reads another asset class's silver table %s" % (f, a.folder, r))
            rf = p.get("dq", {}).get("rules_file")
            if rf:
                if not exists(rf):
                    err("%s: dq rules_file missing" % f)
                else:
                    rs = config.load_yaml(rf, a.variables())
                    if rs["target_table"] != fq:
                        err("%s (%s): target_table %s != %s" % (rf, a.folder, rs["target_table"], fq))
                    miss = rule_columns(rs) - gold_cols[fq]
                    if miss:
                        err("%s (%s): rules refer to columns not in the product: %s" % (rf, a.folder, sorted(miss)))
            for k in ("business_purpose", "grain", "owner", "refresh_pattern", "intended_consumers"):
                if k not in p["documentation"]:
                    err("%s: documentation.%s missing" % (f, k))
            done_here.add(item)

    # ---- governance
    acc = config.load_yaml("definitions/governance/access.yml")
    products = {item for a in acs for item in a.items.get("gold", [])}
    for g in acc["grants"]:
        t = g["on"]
        if t["type"] == "GOLD_PRODUCT" and t["name"] not in products:
            err("access.yml: GOLD_PRODUCT %s is not built by any pipeline" % t["name"])
        if t["type"] == "TABLE" and t["name"] not in gold_targets and t["name"] not in silver_targets:
            err("access.yml: grant on unknown table %s" % t["name"])
        if g["principal"] not in acc["groups"]:
            err("access.yml: principal %s not declared in groups" % g["principal"])
    for mk in config.load_yaml("definitions/governance/masking.yml")["masks"]:
        if mk["table"] not in silver_cols or mk["column"] not in silver_cols[mk["table"]]:
            err("masking.yml: %s.%s does not exist" % (mk["table"], mk["column"]))
    for p in config.load_yaml("definitions/governance/lineage.yml", dummy)["products"]:
        if p not in products:
            err("lineage.yml: product %s unknown" % p)
    for a in acs:
        if a.prefix == "common":
            continue
        for ent, t in config.load_yaml("definitions/governance/lineage.yml", a.variables())["record_trace"].items():
            if t["silver_table"] not in silver_targets or t["bronze_table"] not in bronze_targets:
                err("lineage.yml: record_trace %s unresolved for %s" % (ent, a.folder))
    return errors, warns
