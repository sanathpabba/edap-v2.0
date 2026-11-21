-- One-time Unity Catalog setup for EDAP 2.0. Run as a metastore admin on the v2-0 workspace.
-- NOTE: if the metastore has no storage root, add MANAGED LOCATION 'abfss://<container>@edapdl.dfs.core.windows.net/...'
-- (needs an external location backed by the access connector edap-databricks-access-connector).
CREATE CATALOG IF NOT EXISTS edap COMMENT 'EDAP 2.0 - Enterprise Data Analytical Platform';
CREATE SCHEMA IF NOT EXISTS edap.bronze;
CREATE SCHEMA IF NOT EXISTS edap.silver;
CREATE SCHEMA IF NOT EXISTS edap.gold;
CREATE SCHEMA IF NOT EXISTS edap.consumption;
CREATE SCHEMA IF NOT EXISTS edap.reference;
CREATE SCHEMA IF NOT EXISTS edap.metadata;
CREATE SCHEMA IF NOT EXISTS edap.quarantine;
CREATE SCHEMA IF NOT EXISTS edap.monitoring;
CREATE SCHEMA IF NOT EXISTS edap.audit;
CREATE SCHEMA IF NOT EXISTS edap.governance;   -- holds column-mask functions
CREATE VOLUME IF NOT EXISTS edap.metadata.artifacts COMMENT 'Build artifacts: edap_framework wheels (tools/publish_wheel.sh)';
