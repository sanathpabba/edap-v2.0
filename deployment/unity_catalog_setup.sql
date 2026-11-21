-- Unity Catalog setup for EDAP 2.0, exactly as applied to the v2-0 workspace on 2026-11-21 (run as a metastore admin).
-- The metastore is shared with 1.0: its catalogs (edap_prod, edap_databricks_workspace*) are untouched.
--
-- Reused from 1.0 (already exist, do not recreate):
--   storage credential edap_storage_credential  (access connector edap-databricks-access-connector)
--   external locations  edap_landing, edap_bronze, edap_silver, edap_gold, edap_metadata, edap_platinum  (one per container of storage account edapdl)
--
-- 0. New storage container for the simulated source system (shell, not SQL):
--      az storage fs create -n sourcedrop --account-name edapdl --auth-mode login

-- 1. External location for it (validated: READ, LIST, WRITE, DELETE pass)
CREATE EXTERNAL LOCATION IF NOT EXISTS edap_sourcedrop
  URL 'abfss://sourcedrop@edapdl.dfs.core.windows.net/'
  WITH (STORAGE CREDENTIAL edap_storage_credential)
  COMMENT 'EDAP 2.0: simulated source system storage (position files)';

-- 2. Catalog: managed location next to (not inside) 1.0's metadata/catalog folder
CREATE CATALOG IF NOT EXISTS edap
  MANAGED LOCATION 'abfss://metadata@edapdl.dfs.core.windows.net/edap'
  COMMENT 'EDAP 2.0 - Enterprise Data Analytical Platform (synthetic capital-markets data)';

-- 3. Medallion schemas keep their managed tables in the matching container; consumption uses the platinum container.
--    Checkpoints and landing files live outside these /managed folders (inside the same external locations).
CREATE SCHEMA IF NOT EXISTS edap.bronze      MANAGED LOCATION 'abfss://bronze@edapdl.dfs.core.windows.net/managed'   COMMENT 'Raw append-only Delta copies with audit and lineage columns';
CREATE SCHEMA IF NOT EXISTS edap.silver      MANAGED LOCATION 'abfss://silver@edapdl.dfs.core.windows.net/managed'   COMMENT 'Canonical, deduplicated, validated enterprise entities';
CREATE SCHEMA IF NOT EXISTS edap.gold        MANAGED LOCATION 'abfss://gold@edapdl.dfs.core.windows.net/managed'     COMMENT 'Reusable business data products';
CREATE SCHEMA IF NOT EXISTS edap.consumption MANAGED LOCATION 'abfss://platinum@edapdl.dfs.core.windows.net/managed' COMMENT 'Consumer-specific serving objects over Gold';

-- 4. Supporting schemas use the catalog's default location
CREATE SCHEMA IF NOT EXISTS edap.landing     COMMENT 'EDAP 2.0 landing';
CREATE SCHEMA IF NOT EXISTS edap.reference   COMMENT 'EDAP 2.0 reference';
CREATE SCHEMA IF NOT EXISTS edap.metadata    COMMENT 'EDAP 2.0 metadata';
CREATE SCHEMA IF NOT EXISTS edap.quarantine  COMMENT 'EDAP 2.0 quarantine';
CREATE SCHEMA IF NOT EXISTS edap.monitoring  COMMENT 'EDAP 2.0 monitoring';
CREATE SCHEMA IF NOT EXISTS edap.audit       COMMENT 'EDAP 2.0 audit';
CREATE SCHEMA IF NOT EXISTS edap.governance  COMMENT 'EDAP 2.0 governance (column-mask functions)';

-- 5. Volume for the framework wheels (tools/publish_wheel.sh uploads here)
CREATE VOLUME IF NOT EXISTS edap.metadata.artifacts COMMENT 'Build artifacts: edap_framework wheels (tools/publish_wheel.sh)';

-- Catalog/schema descriptions and tags are applied from definitions/governance/ownership.yml by runners/governance_apply.py --step ownership.
-- Grants to the persona groups come later (the groups must exist at account level first): runners/governance_apply.py --step grants.
