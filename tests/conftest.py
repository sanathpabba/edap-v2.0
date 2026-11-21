import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("EDAP_PROJECT_ROOT", ROOT)
sys.path.insert(0, ROOT)

try:                                    # unit tests must run without a Spark install
    import pyspark  # noqa: F401
except ImportError:
    for n in ("pyspark", "pyspark.sql", "pyspark.sql.functions", "pyspark.dbutils"):
        sys.modules.setdefault(n, types.ModuleType(n))
    sys.modules["pyspark.sql"].functions = sys.modules["pyspark.sql.functions"]
    sys.modules["pyspark.sql"].Window = object
