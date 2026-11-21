"""Reference data management: governed code lists loaded from definitions/reference_data/*.yml into edap.reference.<name>.
Every row carries code + effective_from/effective_to + active_flag + version + owner + source (spec section 18).
Re-loading a changed version closes the old rows (effective_to, active_flag=false) and inserts the new ones: history is kept."""
import datetime as dt

from pyspark.sql import functions as F

from edap_framework.core import config


def list_reference():
    import os
    d = os.path.join(config.project_root(), "definitions", "reference_data")
    return sorted(f[:-4] for f in os.listdir(d) if f.endswith(".yml"))


def load_reference(spark, name, env):
    spec = config.load_yaml("definitions/reference_data/%s.yml" % name)
    fq = "%s.reference.%s" % (env["catalog"], spec["reference"])
    spark.sql("CREATE SCHEMA IF NOT EXISTS %s.reference" % env["catalog"])
    ddl = ", ".join("%s %s" % kv for kv in spec["columns"].items())
    df = (spark.createDataFrame([tuple(r[c] for c in spec["columns"]) for r in spec["rows"]], ddl)
          .withColumn("effective_from", F.to_date(F.lit(spec["effective_from"])))
          .withColumn("effective_to", F.lit(None).cast("date"))
          .withColumn("active_flag", F.lit(True))
          .withColumn("version", F.lit(int(spec["version"])))
          .withColumn("owner", F.lit(spec["owner"]))
          .withColumn("source", F.lit(spec["source"])))
    if not spark.catalog.tableExists(fq):
        df.write.saveAsTable(fq)
        n = df.count()
    else:
        cur = spark.table(fq).where("active_flag").agg(F.max("version")).collect()[0][0] or 0
        if int(spec["version"]) <= cur:
            return 0                                           # nothing new
        spark.sql("UPDATE %s SET active_flag = false, effective_to = current_date() WHERE active_flag" % fq)
        df.withColumn("effective_from", F.current_date()).write.mode("append").saveAsTable(fq)
        n = df.count()
    spark.sql("COMMENT ON TABLE %s IS '%s'" % (fq, spec["description"].replace("'", "''")))
    spark.sql("ALTER TABLE %s SET TAGS ('layer' = 'reference', 'owner' = '%s', 'source' = '%s')" % (fq, spec["owner"], spec["source"].replace("'", "")))
    return n
