#!/bin/bash

# Set OpenSSL 3 library path for ODBC driver
export DYLD_LIBRARY_PATH=/opt/homebrew/Cellar/openssl@3/3.5.9/lib:$DYLD_LIBRARY_PATH

# Load Azure config
source azure_config.env

# Connect using sqlcmd
/opt/homebrew/opt/mssql-tools18/bin/sqlcmd \
  -S tcp:${SQL_SERVER_NAME}.database.windows.net,1433 \
  -d $SQL_DATABASE_NAME \
  -U $SQL_ADMIN_USER \
  -P "$SQL_ADMIN_PASSWORD" \
  -C \
  "$@"
