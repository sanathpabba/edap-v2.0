# EDAP - Unity Catalog Setup Guide

**Created**: 2026-11-19  
**Status**: ✅ All Azure Resources Ready

---

## ✅ Infrastructure Complete

### ADLS Gen2 Storage Account
- **Name**: `edapdl`
- **Type**: ADLS Gen2 (Hierarchical Namespace)
- **Location**: Central US
- **URL**: https://edapdl.dfs.core.windows.net

### Containers Created
- ✅ `landing` - Raw files as they arrive
- ✅ `bronze` - Raw data, no transformations
- ✅ `silver` - Cleansed and standardized
- ✅ `gold` - Business aggregates
- ✅ `platinum` - ML features
- ✅ `metadata` - Logs, checkpoints, configs

### Access Connector
- **Name**: `edap-databricks-access-connector`
- **Principal ID**: `3167d2a2-1a81-40eb-8617-8e567d3e33f8`
- **Role**: Storage Blob Data Contributor
- **Status**: ✅ Permissions granted

---

## 🚀 Unity Catalog Setup in Databricks

### Step 1: Launch Databricks Workspace

👉 **https://adb-7405612919129990.10.azuredatabricks.net**

Login with: `2024hb21330@wilp.bits-pilani.ac.in`

---

### Step 2: Create Unity Catalog Metastore

**Navigate**: Left sidebar → **Catalog** → Click **"Set up Unity Catalog"** or **"Create Metastore"**

**Configuration**:
```
Metastore name:        edap-metastore
Region:                Central US
Storage location:      abfss://metadata@edapdl.dfs.core.windows.net/metastore
Access connector:      /subscriptions/1bd38212-4f79-42c0-b758-37a56d9ebc7e/resourceGroups/edap-rg/providers/Microsoft.Databricks/accessConnectors/edap-databricks-access-connector
```

**Important**: The access connector resource ID is:
```
/subscriptions/1bd38212-4f79-42c0-b758-37a56d9ebc7e/resourceGroups/edap-rg/providers/Microsoft.Databricks/accessConnectors/edap-databricks-access-connector
```

Click **Create** → Wait 2-3 minutes

---

### Step 3: Create Storage Credentials

Create a new **SQL notebook** and run:

```sql
-- Create storage credential using the access connector
CREATE STORAGE CREDENTIAL IF NOT EXISTS azure_storage_credential
WITH (
  AZURE_MANAGED_IDENTITY '/subscriptions/1bd38212-4f79-42c0-b758-37a56d9ebc7e/resourceGroups/edap-rg/providers/Microsoft.Databricks/accessConnectors/edap-databricks-access-connector'
);

-- Verify
DESCRIBE STORAGE CREDENTIAL azure_storage_credential;
```

---

### Step 4: Create External Locations

```sql
-- Landing zone external location
CREATE EXTERNAL LOCATION IF NOT EXISTS landing_location
URL 'abfss://landing@edapdl.dfs.core.windows.net/'
WITH (STORAGE CREDENTIAL azure_storage_credential)
COMMENT 'Raw files landing zone';

-- Bronze layer external location
CREATE EXTERNAL LOCATION IF NOT EXISTS bronze_location
URL 'abfss://bronze@edapdl.dfs.core.windows.net/'
WITH (STORAGE CREDENTIAL azure_storage_credential)
COMMENT 'Bronze layer - raw data';

-- Silver layer external location
CREATE EXTERNAL LOCATION IF NOT EXISTS silver_location
URL 'abfss://silver@edapdl.dfs.core.windows.net/'
WITH (STORAGE CREDENTIAL azure_storage_credential)
COMMENT 'Silver layer - cleansed data';

-- Gold layer external location
CREATE EXTERNAL LOCATION IF NOT EXISTS gold_location
URL 'abfss://gold@edapdl.dfs.core.windows.net/'
WITH (STORAGE CREDENTIAL azure_storage_credential)
COMMENT 'Gold layer - business aggregates';

-- Platinum layer external location
CREATE EXTERNAL LOCATION IF NOT EXISTS platinum_location
URL 'abfss://platinum@edapdl.dfs.core.windows.net/'
WITH (STORAGE CREDENTIAL azure_storage_credential)
COMMENT 'Platinum layer - ML features';

-- Metadata external location
CREATE EXTERNAL LOCATION IF NOT EXISTS metadata_location
URL 'abfss://metadata@edapdl.dfs.core.windows.net/'
WITH (STORAGE CREDENTIAL azure_storage_credential)
COMMENT 'Metadata - logs and checkpoints';

-- Verify all locations
SHOW EXTERNAL LOCATIONS;
```

---

### Step 5: Create Catalog and Schemas

```sql
-- Create main catalog
CREATE CATALOG IF NOT EXISTS edap_prod
COMMENT 'EDAP Production Catalog - Capital Markets Data Platform';

-- Use the catalog
USE CATALOG edap_prod;

-- Create Bronze schema with external location
CREATE SCHEMA IF NOT EXISTS bronze
MANAGED LOCATION 'abfss://bronze@edapdl.dfs.core.windows.net/'
COMMENT 'Bronze layer - Raw data from sources, no transformations';

-- Create Silver schema with external location
CREATE SCHEMA IF NOT EXISTS silver
MANAGED LOCATION 'abfss://silver@edapdl.dfs.core.windows.net/'
COMMENT 'Silver layer - Cleansed, validated, and standardized data';

-- Create Gold schema with external location
CREATE SCHEMA IF NOT EXISTS gold
MANAGED LOCATION 'abfss://gold@edapdl.dfs.core.windows.net/'
COMMENT 'Gold layer - Business-ready aggregated data';

-- Create Platinum schema with external location
CREATE SCHEMA IF NOT EXISTS platinum
MANAGED LOCATION 'abfss://platinum@edapdl.dfs.core.windows.net/'
COMMENT 'Platinum layer - ML features and advanced analytics';

-- Verify schemas
SHOW SCHEMAS IN edap_prod;

-- Show schema details
DESCRIBE SCHEMA EXTENDED edap_prod.bronze;
DESCRIBE SCHEMA EXTENDED edap_prod.silver;
DESCRIBE SCHEMA EXTENDED edap_prod.gold;
DESCRIBE SCHEMA EXTENDED edap_prod.platinum;
```

---

### Step 6: Test Storage Access

Create a **Python notebook** to verify storage access:

```python
# Test writing to Bronze layer
test_data = [(1, "test", "2026-11-19")]
df = spark.createDataFrame(test_data, ["id", "name", "date"])

# Write to Bronze
df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("edap_prod.bronze.test_table")

print("✅ Bronze layer write successful!")

# Read back
df_read = spark.table("edap_prod.bronze.test_table")
display(df_read)

# Clean up test table
spark.sql("DROP TABLE IF EXISTS edap_prod.bronze.test_table")
print("✅ Test complete - storage access working!")
```

---

## 📥 Bronze Layer Ingestion from Azure SQL

Now you can ingest your SQL data to Bronze layer with Unity Catalog!

Create a **Python notebook** called `Bronze_Layer_Ingestion`:

```python
# JDBC connection configuration
jdbc_hostname = "edap-sql-bbe209.database.windows.net"
jdbc_port = 1433
jdbc_database = "edap-source-db"
jdbc_username = "edapadmin"
jdbc_password = "<SQL_ADMIN_PASSWORD - stored in Key Vault>"

jdbc_url = f"jdbc:sqlserver://{jdbc_hostname}:{jdbc_port};database={jdbc_database};encrypt=true;trustServerCertificate=false;hostNameInCertificate=*.database.windows.net;loginTimeout=30;"

connection_properties = {
    "user": jdbc_username,
    "password": jdbc_password,
    "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver"
}

# Tables to ingest
tables = {
    "reference.instruments": "bronze.reference_instruments",
    "reference.portfolios": "bronze.reference_portfolios",
    "reference.counterparties": "bronze.reference_counterparties",
    "reference.accounts": "bronze.reference_accounts",
    "source.trades": "bronze.source_trades"
}

# Ingest each table to Bronze layer in ADLS Gen2
for sql_table, bronze_table in tables.items():
    print(f"📥 Loading {sql_table}...")
    
    # Read from Azure SQL
    df = spark.read.jdbc(
        url=jdbc_url,
        table=sql_table,
        properties=connection_properties
    )
    
    row_count = df.count()
    
    # Write to Bronze layer (Unity Catalog managed table in ADLS Gen2)
    df.write \
        .format("delta") \
        .mode("overwrite") \
        .option("overwriteSchema", "true") \
        .option("delta.enableChangeDataFeed", "true") \
        .saveAsTable(f"edap_prod.{bronze_table}")
    
    print(f"✅ {bronze_table}: {row_count} rows written to ADLS Gen2")
    print(f"   Location: abfss://bronze@edapdl.dfs.core.windows.net/{bronze_table}")
    print()

print("🎉 Bronze layer ingestion complete!")
print("All data is now in ADLS Gen2 Delta Lake format with Unity Catalog!")
```

---

## ✅ Verify Bronze Layer

```sql
-- Use the catalog
USE CATALOG edap_prod;

-- Show all Bronze tables
SHOW TABLES IN bronze;

-- Check row counts
SELECT 'reference_instruments' as table_name, COUNT(*) as row_count FROM bronze.reference_instruments
UNION ALL SELECT 'reference_portfolios', COUNT(*) FROM bronze.reference_portfolios
UNION ALL SELECT 'reference_counterparties', COUNT(*) FROM bronze.reference_counterparties
UNION ALL SELECT 'reference_accounts', COUNT(*) FROM bronze.reference_accounts
UNION ALL SELECT 'source_trades', COUNT(*) FROM bronze.source_trades;

-- Check table properties (verify Delta Lake and storage location)
DESCRIBE EXTENDED bronze.source_trades;

-- Sample data from Bronze
SELECT * FROM bronze.source_trades LIMIT 10;
```

**Expected Output**:
```
table_name                  | row_count
----------------------------|----------
reference_instruments       | 100
reference_portfolios        | 20
reference_counterparties    | 30
reference_accounts          | 40
source_trades               | 5000
```

---

## 🎯 Unity Catalog Benefits

### ✅ What You Now Have

1. **3-Layer Namespace**
   - Catalog: `edap_prod`
   - Schema: `bronze`, `silver`, `gold`, `platinum`
   - Table: `reference_instruments`, `source_trades`, etc.

2. **Centralized Governance**
   - All data stored in ADLS Gen2
   - Managed via Unity Catalog
   - Fine-grained access control
   - Audit logging enabled

3. **Delta Lake Format**
   - ACID transactions
   - Time travel
   - Schema evolution
   - Change Data Feed enabled

4. **Storage Separation**
   - Each layer in its own container
   - Clear data lifecycle
   - Easy to manage and monitor

---

## 📊 Data Flow Architecture

```
Azure SQL Database (edap-source-db)
         │
         │ JDBC Ingestion
         ↓
Unity Catalog: edap_prod.bronze (ADLS Gen2: abfss://bronze@edapdl/)
├── reference_instruments (100 rows)
├── reference_portfolios (20 rows)
├── reference_counterparties (30 rows)
├── reference_accounts (40 rows)
└── source_trades (5,000 rows)
         │
         │ Transformation
         ↓
Unity Catalog: edap_prod.silver (ADLS Gen2: abfss://silver@edapdl/)
├── dim_instruments
├── dim_portfolios
├── dim_counterparties
├── dim_accounts
└── fact_trades
         │
         │ Aggregation
         ↓
Unity Catalog: edap_prod.gold (ADLS Gen2: abfss://gold@edapdl/)
├── daily_portfolio_positions
├── trade_analytics
└── risk_metrics
         │
         │ Feature Engineering
         ↓
Unity Catalog: edap_prod.platinum (ADLS Gen2: abfss://platinum@edapdl/)
├── ml_features
└── predictions
```

---

## 🔐 Security Best Practices

### Current Setup ✅
- Access Connector with Managed Identity
- RBAC on storage account
- Unity Catalog governance

### Future Enhancements (TODO)
1. Move SQL credentials to Azure Key Vault
2. Use Databricks Secret Scopes
3. Enable IP Access Lists
4. Set up table-level permissions
5. Enable audit logging to Log Analytics

---

## 💰 Cost Tracking

### Storage Costs
- **ADLS Gen2**: ~$0.02 per GB/month
- **Current data**: ~5MB = <$0.01/month
- **Delta Lake metadata**: Minimal

### Compute Costs
- Charged only when clusters are running
- Single Node: ~$0.30/hour
- Stop clusters when not in use!

---

## 🆘 Troubleshooting

### "Cannot access storage"
- Verify Access Connector role assignment
- Check storage account firewall rules
- Ensure hierarchical namespace is enabled

### "External location not found"
- Verify storage credential exists
- Check external location URLs (must be `abfss://`)
- Ensure access connector resource ID is correct

### "Table already exists"
- Use `IF NOT EXISTS` in CREATE statements
- Or use `DROP TABLE` before recreating
- Or use `REPLACE` instead of `CREATE`

---

## 📚 Reference

### Storage URLs
```
Landing:   abfss://landing@edapdl.dfs.core.windows.net/
Bronze:    abfss://bronze@edapdl.dfs.core.windows.net/
Silver:    abfss://silver@edapdl.dfs.core.windows.net/
Gold:      abfss://gold@edapdl.dfs.core.windows.net/
Platinum:  abfss://platinum@edapdl.dfs.core.windows.net/
Metadata:  abfss://metadata@edapdl.dfs.core.windows.net/
```

### Access Connector Resource ID
```
/subscriptions/1bd38212-4f79-42c0-b758-37a56d9ebc7e/resourceGroups/edap-rg/providers/Microsoft.Databricks/accessConnectors/edap-databricks-access-connector
```

### Principal ID
```
3167d2a2-1a81-40eb-8617-8e567d3e33f8
```

---

**🎉 Unity Catalog setup complete - ready for Bronze layer ingestion! 🎉**

---

*Generated: 2026-11-19 22:50*
