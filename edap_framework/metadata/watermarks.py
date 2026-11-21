"""Watermark store (edap.metadata.watermarks): one row per source object, advanced only after a successful landing write."""
WM_DDL = """CREATE TABLE IF NOT EXISTS {t} (
  watermark_key STRING, watermark_value TIMESTAMP, batch_id STRING, updated_ts TIMESTAMP)"""


def get_watermark(spark, store, key):
    spark.sql(WM_DDL.format(t=store))
    rows = spark.sql("SELECT watermark_value FROM %s WHERE watermark_key = '%s'" % (store, key)).collect()
    return rows[0][0] if rows else None


def set_watermark(spark, store, key, value, batch_id):
    spark.sql(WM_DDL.format(t=store))
    spark.createDataFrame([(key, value, batch_id)], "watermark_key string, watermark_value timestamp, batch_id string") \
         .createOrReplaceTempView("_wm_new")
    spark.sql("""MERGE INTO %s t USING (SELECT *, current_timestamp() AS updated_ts FROM _wm_new) s
                 ON t.watermark_key = s.watermark_key
                 WHEN MATCHED THEN UPDATE SET watermark_value = s.watermark_value, batch_id = s.batch_id, updated_ts = s.updated_ts
                 WHEN NOT MATCHED THEN INSERT *""" % store)
