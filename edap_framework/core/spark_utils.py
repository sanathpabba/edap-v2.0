"""Spark/Databricks helpers: dbutils access, secrets by logical name, table naming."""


def get_dbutils(spark):
    try:
        from pyspark.dbutils import DBUtils
        return DBUtils(spark)
    except Exception:
        import IPython
        return IPython.get_ipython().user_ns["dbutils"]


def secret(spark, env, logical_name):
    return get_dbutils(spark).secrets.get(scope=env["secrets"]["scope"], key=env["secrets"]["keys"][logical_name])


def fq_table(target):
    return "%s.%s.%s" % (target["catalog"], target["schema"], target["table"])
