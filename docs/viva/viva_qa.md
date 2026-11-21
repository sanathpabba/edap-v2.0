# Viva Q&A preparation (draft)

**Why YAML for everything?** So an institution onboards a source, rule, mapping or product by editing configuration, not code. The framework
contains no table- or column-specific logic; adding a SQL table is a source-contract entry plus one scaffold command, validated offline.

**What went wrong in 1.0 and what changed?** Hard-coded notebooks, mismatched IDs across sources, custom DQ instead of DQX, and completion
claims without evidence. 2.0: one master ID format, definitions-driven code, DQX, and a tracker where a task is DONE only with evidence.

**Why DQX rather than custom checks or DLT expectations?** It is an open-source Databricks Labs framework with declarative checks, row-level
reasons and quarantine support; rules are YAML metadata, matching the dissertation's configuration principle.

**Why DQ at both Bronze and Silver?** Bronze asks "is it technically readable?" (format, completeness, domain); Silver asks "does it satisfy
enterprise rules?" (referential integrity, business dates, status). Bronze keeps every row so nothing is lost; bad rows are copied to quarantine.

**Why a canonical model in Silver?** Each source names things differently (sec_code / instrument_code / instrument_id). Silver maps them once
into one enterprise representation so every Gold product reuses the same entities.

**Why do Gold products instead of one table per report?** Reuse: four products (trade analytics, position and exposure, P&L, regulatory) plus
one conformed FX dimension serve many consumers; the USD conversion rule exists in one place.

**How do you handle late-arriving and duplicate data?** Dedup on business key with explicit ordering; MERGE only updates when the incoming
record is newer (source timestamp or file version); events are immutable so duplicates are ignored. The injected counts are known, so results can be checked.

**How do you know the data was synthetic but realistic?** Seeded generators; prices within 2% of real daily market prices; real FX rates from a
public API; 25 validation checks including arithmetic, lifecycle and referential consistency (see evidence index).

**How is lineage handled?** Unity Catalog captures table and column lineage automatically; the framework adds file/batch/run-level columns
(`_source_file`, `_landing_batch_id`, `_batch_id`, `_run_id`, `_row_hash`, `_spec_path`) and a record-trace function.

**How is governance demonstrated?** Ownership and sensitivity tags from YAML, persona grants with a denied-access demonstration, and a column
mask on the legal entity identifier.

**What are the limitations?** Synthetic data and one cloud/platform; small volumes; Landing/Bronze to Gold validated on a single workspace;
UC lineage depends on Databricks compute; the Consumption layer is a thin serving view over Gold.

**How would another institution adopt it?** Replace source contracts, mappings, reference data and product YAMLs; keep the engines.
