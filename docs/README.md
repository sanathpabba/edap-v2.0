# Enterprise Data Analytical Platform (EDAP)

MBA Dissertation: A medallion-architecture (Landing → Bronze → Silver → Gold → Platinum) data platform on Azure Databricks for capital-markets data modernization.

**Key Features**: Unity Catalog governance, DQX data quality, metadata-driven processing, 4 source systems, end-to-end lineage.

## 🚀 Quick Start

### Step 1: Check Prerequisites

```bash
cd EDAP
./check_prerequisites.sh
```

### Step 2: Fix Any Issues

If Azure CLI is missing (most common issue):

```bash
./install_azure_cli.sh
```

See **FIX_ISSUES.md** for help fixing any issues.

### Step 3: Run Infrastructure Setup

```bash
./setup_azure_infrastructure.sh
```

This creates all Azure resources in 15-20 minutes.

## 📚 Documentation

- **FIX_ISSUES.md** - Fix missing prerequisites (START HERE if issues)
- **QUICK_START.md** - Complete setup walkthrough
- **INSTALL_PREREQUISITES.md** - Detailed installation guide
- **PROJECT_CHECKLIST.md** - Track all 161 tasks
- **00_INFRASTRUCTURE_SETUP_GUIDE.md** - Manual setup alternative
- **SETUP_SUMMARY.md** - Complete package overview

## 📂 Project Structure

See `21_docs/` for architecture diagrams, data models, and operational runbooks.
