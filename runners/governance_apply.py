"""Governance as code: ownership/tags, grants, masks, lineage report, record trace.
   python runners/governance_apply.py --step ownership|grants|masks|lineage|all [--dry-run]
   python runners/governance_apply.py --step trace --entity trade --key TRD0000001"""
import argparse
import json

import _bootstrap
from edap_framework.governance import apply

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["ownership", "grants", "masks", "lineage", "trace", "all"], required=True)
    ap.add_argument("--dry-run", action="store_true", help="print GRANT statements only")
    ap.add_argument("--entity"); ap.add_argument("--key"); _bootstrap.add_run_id(ap)
    a = ap.parse_args(); _bootstrap.apply_run_id(a)
    spark = _bootstrap.spark_session()
    if a.step in ("ownership", "all"): print("schemas described:", apply.apply_ownership(spark))
    if a.step in ("grants", "all"):
        for s in apply.apply_grants(spark, dry_run=a.dry_run): print(s)
    if a.step in ("masks", "all"): print("masks:", apply.apply_masks(spark))
    if a.step in ("lineage", "all"): print("lineage rows:", apply.lineage_report(spark))
    if a.step == "trace": print(json.dumps(apply.trace_record(spark, a.entity, a.key), indent=2, default=str))
