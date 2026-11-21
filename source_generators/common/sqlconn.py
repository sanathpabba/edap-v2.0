import pyodbc
from . import secrets


def connect(autocommit=False):
    cs = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={secrets.get('sql-server-name')}.database.windows.net;"
        f"DATABASE={secrets.get('sql-database-name')};"
        f"UID={secrets.get('sql-admin-user')};PWD={secrets.get('sql-admin-password')};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30"
    )
    return pyodbc.connect(cs, autocommit=autocommit)
