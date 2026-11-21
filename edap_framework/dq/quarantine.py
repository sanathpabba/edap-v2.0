"""Quarantine helpers: keep bad Bronze rows out of Silver, and close them out when a correction arrives."""
from pyspark.sql import functions as F


def exclude_quarantined(spark, df, env, bronze_table):
    """Drop Bronze rows that DQ quarantined (status OPEN). bronze_table = full name, e.g. edap.bronze.equities_file_positions. Matches on table + _row_hash."""
    q = "%s.quarantine.bronze_invalid" % env["catalog"]
    if not spark.catalog.tableExists(q):
        return df
    bad = spark.table(q).where((F.col("table_name") == bronze_table) & (F.col("status") == "OPEN")) \
               .select(F.col("row_hash").alias("_q_hash")).distinct()
    return df.join(F.broadcast(bad), df["_row_hash"] == bad["_q_hash"], "left_anti")


def close_superseded_by_resend(spark, env, bronze_table, business_date_json_field="file_business_date"):
    """A corrected file (higher version, same business date) supersedes the quarantined rows of the earlier version."""
    q = "%s.quarantine.bronze_invalid" % env["catalog"]
    bronze = bronze_table
    spark.sql("""
      MERGE INTO {q} t
      USING (SELECT file_business_date AS bd, MAX(CAST(file_version AS INT)) AS max_v FROM {b} GROUP BY file_business_date) s
      ON t.table_name = '{n}' AND t.status = 'OPEN'
         AND get_json_object(t.record_json, '$.{f}') = s.bd
         AND CAST(get_json_object(t.record_json, '$.file_version') AS INT) < s.max_v
      WHEN MATCHED THEN UPDATE SET t.status = 'SUPERSEDED_BY_RESEND', t.resolved_ts = current_timestamp(),
                                   t.resolution = 'corrected file received (higher version, same business date)'
    """.format(q=q, b=bronze, n=bronze_table, f=business_date_json_field))
