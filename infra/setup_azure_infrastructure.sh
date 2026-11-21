#!/bin/bash

################################################################################
# EDAP Azure Infrastructure Setup Script
# 
# Purpose: Automated setup of all Azure resources for EDAP
# Usage: ./setup_azure_infrastructure.sh
# 
# Prerequisites:
#   - Azure CLI installed (az command available)
#   - Logged in to Azure (az login)
#   - Appropriate subscription selected
#
# This script will create:
#   - Resource Group
#   - Azure SQL Database
#   - Azure Databricks Workspace
#   - Storage Account (ADLS Gen2)
#   - Event Hub
#   - Key Vault
#   - Service Principal
#
################################################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  $1"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is not installed. Please install it first."
        exit 1
    fi
}

# Check prerequisites
print_header "Checking Prerequisites"

check_command az
check_command jq
check_command curl

# Check Azure login
if ! az account show &> /dev/null; then
    print_error "Not logged in to Azure. Please run 'az login' first."
    exit 1
fi

print_success "All prerequisites met"

# Display current subscription
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
print_info "Using subscription: $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)"

echo ""
read -p "Continue with this subscription? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Setup cancelled. Use 'az account set --subscription <id>' to change subscription."
    exit 1
fi

# Configuration variables
print_header "Configuration"

# Allow user to customize or use defaults
read -p "Enter Resource Group name [edap-rg]: " RESOURCE_GROUP
RESOURCE_GROUP=${RESOURCE_GROUP:-edap-rg}

read -p "Enter Azure Location [eastus]: " LOCATION
LOCATION=${LOCATION:-eastus}

PROJECT_TAG="EDAP-MBA-Dissertation"

print_info "Resource Group: $RESOURCE_GROUP"
print_info "Location: $LOCATION"
print_info "Project Tag: $PROJECT_TAG"

echo ""
read -p "Proceed with setup? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Setup cancelled."
    exit 1
fi

# Create Resource Group
print_header "Step 1/9: Creating Resource Group"

if az group show --name $RESOURCE_GROUP &> /dev/null; then
    print_warning "Resource group $RESOURCE_GROUP already exists. Using existing."
else
    az group create \
      --name $RESOURCE_GROUP \
      --location $LOCATION \
      --tags Project=$PROJECT_TAG Environment=Dev \
      --output none
    print_success "Resource group created: $RESOURCE_GROUP"
fi

# SQL Server Setup
print_header "Step 2/9: Creating Azure SQL Database"

SQL_SERVER_NAME="edap-sql-server-$(openssl rand -hex 4)"
SQL_ADMIN_USER="edapadmin"
SQL_ADMIN_PASSWORD="EDAP@Pass$(openssl rand -hex 4)123!"
SQL_DATABASE_NAME="edap-source-db"

print_info "Creating SQL Server: $SQL_SERVER_NAME"

az sql server create \
  --name $SQL_SERVER_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --admin-user $SQL_ADMIN_USER \
  --admin-password "$SQL_ADMIN_PASSWORD" \
  --tags Project=$PROJECT_TAG Component=SourceSystem \
  --output none

print_success "SQL Server created"

# Configure SQL firewall
print_info "Configuring firewall rules..."

az sql server firewall-rule create \
  --server $SQL_SERVER_NAME \
  --resource-group $RESOURCE_GROUP \
  --name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0 \
  --output none

MY_IP=$(curl -s ifconfig.me)
az sql server firewall-rule create \
  --server $SQL_SERVER_NAME \
  --resource-group $RESOURCE_GROUP \
  --name AllowMyIP \
  --start-ip-address $MY_IP \
  --end-ip-address $MY_IP \
  --output none

print_success "Firewall rules configured"

# Create database
print_info "Creating database: $SQL_DATABASE_NAME"

az sql db create \
  --server $SQL_SERVER_NAME \
  --resource-group $RESOURCE_GROUP \
  --name $SQL_DATABASE_NAME \
  --service-objective Basic \
  --backup-storage-redundancy Local \
  --tags Project=$PROJECT_TAG Component=SourceSystem Type=Transactional \
  --output none

SQL_CONNECTION_STRING="Server=tcp:${SQL_SERVER_NAME}.database.windows.net,1433;Initial Catalog=${SQL_DATABASE_NAME};Persist Security Info=False;User ID=${SQL_ADMIN_USER};Password=${SQL_ADMIN_PASSWORD};MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"

print_success "SQL Database created"

# Databricks Workspace
print_header "Step 3/9: Creating Azure Databricks Workspace"

DATABRICKS_WORKSPACE_NAME="edap-databricks-workspace"
DATABRICKS_PRICING_TIER="premium"

print_info "Creating Databricks workspace (this may take 5-10 minutes)..."

az databricks workspace create \
  --resource-group $RESOURCE_GROUP \
  --name $DATABRICKS_WORKSPACE_NAME \
  --location $LOCATION \
  --sku premium \
  --tags Project=$PROJECT_TAG Component=DataPlatform \
  --output none

DATABRICKS_WORKSPACE_URL=$(az databricks workspace show \
  --resource-group $RESOURCE_GROUP \
  --name $DATABRICKS_WORKSPACE_NAME \
  --query workspaceUrl \
  --output tsv)

print_success "Databricks workspace created"

# Storage Account
print_header "Step 4/9: Creating Storage Account (ADLS Gen2)"

STORAGE_ACCOUNT_NAME="edapstorage$(openssl rand -hex 4)"
STORAGE_CONTAINER_LANDING="landing"
STORAGE_CONTAINER_SOURCE="source"
STORAGE_CONTAINER_ARCHIVE="archive"

print_info "Creating storage account: $STORAGE_ACCOUNT_NAME"

az storage account create \
  --name $STORAGE_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --hierarchical-namespace true \
  --tags Project=$PROJECT_TAG Component=DataLake \
  --output none

STORAGE_ACCOUNT_KEY=$(az storage account keys list \
  --account-name $STORAGE_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "[0].value" \
  --output tsv)

print_success "Storage account created"

# Create containers
print_info "Creating blob containers..."

az storage container create \
  --name $STORAGE_CONTAINER_LANDING \
  --account-name $STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY \
  --output none

az storage container create \
  --name $STORAGE_CONTAINER_SOURCE \
  --account-name $STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY \
  --output none

az storage container create \
  --name $STORAGE_CONTAINER_ARCHIVE \
  --account-name $STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY \
  --output none

# Create folder structure
az storage fs directory create \
  --name "positions/inbound" \
  --file-system $STORAGE_CONTAINER_SOURCE \
  --account-name $STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY \
  --output none

az storage fs directory create \
  --name "positions/archive" \
  --file-system $STORAGE_CONTAINER_SOURCE \
  --account-name $STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY \
  --output none

az storage fs directory create \
  --name "positions/bad" \
  --file-system $STORAGE_CONTAINER_SOURCE \
  --account-name $STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY \
  --output none

print_success "Storage containers and folders created"

# Event Hub
print_header "Step 5/9: Creating Azure Event Hub"

EVENT_HUB_NAMESPACE="edap-eventhub-ns-$(openssl rand -hex 4)"
EVENT_HUB_NAME="trade-events"
EVENT_HUB_CONSUMER_GROUP="databricks-consumer"

print_info "Creating Event Hub namespace: $EVENT_HUB_NAMESPACE"

az eventhubs namespace create \
  --name $EVENT_HUB_NAMESPACE \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Basic \
  --tags Project=$PROJECT_TAG Component=Streaming \
  --output none

az eventhubs eventhub create \
  --name $EVENT_HUB_NAME \
  --namespace-name $EVENT_HUB_NAMESPACE \
  --resource-group $RESOURCE_GROUP \
  --partition-count 2 \
  --message-retention 1 \
  --output none

az eventhubs eventhub consumer-group create \
  --name $EVENT_HUB_CONSUMER_GROUP \
  --eventhub-name $EVENT_HUB_NAME \
  --namespace-name $EVENT_HUB_NAMESPACE \
  --resource-group $RESOURCE_GROUP \
  --output none

EVENT_HUB_CONNECTION_STRING=$(az eventhubs namespace authorization-rule keys list \
  --namespace-name $EVENT_HUB_NAMESPACE \
  --resource-group $RESOURCE_GROUP \
  --name RootManageSharedAccessKey \
  --query primaryConnectionString \
  --output tsv)

print_success "Event Hub created"

# Key Vault
print_header "Step 6/9: Creating Azure Key Vault"

KEY_VAULT_NAME="edap-keyvault-$(openssl rand -hex 4)"

print_info "Creating Key Vault: $KEY_VAULT_NAME"

az keyvault create \
  --name $KEY_VAULT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --tags Project=$PROJECT_TAG Component=Security \
  --output none

print_success "Key Vault created"

# Store secrets
print_header "Step 7/9: Storing Secrets in Key Vault"

print_info "Storing connection strings and credentials..."

az keyvault secret set \
  --vault-name $KEY_VAULT_NAME \
  --name "sql-connection-string" \
  --value "$SQL_CONNECTION_STRING" \
  --output none

az keyvault secret set \
  --vault-name $KEY_VAULT_NAME \
  --name "storage-account-key" \
  --value "$STORAGE_ACCOUNT_KEY" \
  --output none

az keyvault secret set \
  --vault-name $KEY_VAULT_NAME \
  --name "eventhub-connection-string" \
  --value "$EVENT_HUB_CONNECTION_STRING" \
  --output none

az keyvault secret set \
  --vault-name $KEY_VAULT_NAME \
  --name "sql-admin-password" \
  --value "$SQL_ADMIN_PASSWORD" \
  --output none

print_success "Secrets stored in Key Vault"

# Service Principal
print_header "Step 8/9: Creating Service Principal"

SP_NAME="edap-databricks-sp"

print_info "Creating service principal: $SP_NAME"

SP_OUTPUT=$(az ad sp create-for-rbac \
  --name $SP_NAME \
  --role Contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP \
  --output json)

SP_APP_ID=$(echo $SP_OUTPUT | jq -r '.appId')
SP_PASSWORD=$(echo $SP_OUTPUT | jq -r '.password')
SP_TENANT=$(echo $SP_OUTPUT | jq -r '.tenant')

# Grant storage access
az role assignment create \
  --assignee $SP_APP_ID \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT_NAME \
  --output none

# Store in Key Vault
az keyvault secret set \
  --vault-name $KEY_VAULT_NAME \
  --name "sp-app-id" \
  --value "$SP_APP_ID" \
  --output none

az keyvault secret set \
  --vault-name $KEY_VAULT_NAME \
  --name "sp-password" \
  --value "$SP_PASSWORD" \
  --output none

az keyvault secret set \
  --vault-name $KEY_VAULT_NAME \
  --name "sp-tenant" \
  --value "$SP_TENANT" \
  --output none

print_success "Service Principal created and configured"

# Generate Configuration File
print_header "Step 9/9: Generating Configuration Files"

cat > azure_config.env << EOF
# EDAP Azure Configuration
# Generated: $(date)
# DO NOT COMMIT THIS FILE TO GIT - Add to .gitignore

# Resource Group
RESOURCE_GROUP="$RESOURCE_GROUP"
LOCATION="$LOCATION"

# Azure SQL Database
SQL_SERVER_NAME="$SQL_SERVER_NAME"
SQL_ADMIN_USER="$SQL_ADMIN_USER"
SQL_ADMIN_PASSWORD="$SQL_ADMIN_PASSWORD"
SQL_DATABASE_NAME="$SQL_DATABASE_NAME"
SQL_CONNECTION_STRING="$SQL_CONNECTION_STRING"

# Azure Databricks
DATABRICKS_WORKSPACE_NAME="$DATABRICKS_WORKSPACE_NAME"
DATABRICKS_WORKSPACE_URL="$DATABRICKS_WORKSPACE_URL"

# Azure Storage
STORAGE_ACCOUNT_NAME="$STORAGE_ACCOUNT_NAME"
STORAGE_ACCOUNT_KEY="$STORAGE_ACCOUNT_KEY"
STORAGE_CONTAINER_LANDING="$STORAGE_CONTAINER_LANDING"
STORAGE_CONTAINER_SOURCE="$STORAGE_CONTAINER_SOURCE"

# Azure Event Hub
EVENT_HUB_NAMESPACE="$EVENT_HUB_NAMESPACE"
EVENT_HUB_NAME="$EVENT_HUB_NAME"
EVENT_HUB_CONSUMER_GROUP="$EVENT_HUB_CONSUMER_GROUP"
EVENT_HUB_CONNECTION_STRING="$EVENT_HUB_CONNECTION_STRING"

# Azure Key Vault
KEY_VAULT_NAME="$KEY_VAULT_NAME"

# Service Principal
SP_APP_ID="$SP_APP_ID"
SP_PASSWORD="$SP_PASSWORD"
SP_TENANT="$SP_TENANT"

EOF

print_success "Configuration file created: azure_config.env"

# Summary
print_header "Setup Complete! 🎉"

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║          EDAP Azure Infrastructure Summary              ║"
echo "╠════════════════════════════════════════════════════════╣"
echo "║ Resource Group: $RESOURCE_GROUP"
echo "║ Location: $LOCATION"
echo "║"
echo "║ --- Data Sources ---"
echo "║ SQL Server: ${SQL_SERVER_NAME}.database.windows.net"
echo "║ Database: $SQL_DATABASE_NAME"
echo "║ Event Hub: ${EVENT_HUB_NAMESPACE}.servicebus.windows.net"
echo "║"
echo "║ --- Data Platform ---"
echo "║ Databricks: https://$DATABRICKS_WORKSPACE_URL"
echo "║ Storage: ${STORAGE_ACCOUNT_NAME}.dfs.core.windows.net"
echo "║"
echo "║ --- Security ---"
echo "║ Key Vault: https://${KEY_VAULT_NAME}.vault.azure.net"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

print_warning "IMPORTANT: Configuration saved to azure_config.env"
print_warning "DO NOT commit azure_config.env to Git!"
print_warning "Save these credentials in a secure password manager"

echo ""
echo "Next Steps:"
echo "1. Review azure_config.env"
echo "2. Access Databricks workspace: https://$DATABRICKS_WORKSPACE_URL"
echo "3. Enable Unity Catalog in Databricks"
echo "4. Create Databricks cluster"
echo "5. Proceed to Phase 1: Azure SQL source system setup"
echo ""

print_success "Infrastructure setup completed successfully!"
