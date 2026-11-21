"""Registered source transforms for shapes a column mapping cannot express (kept few, referenced by name from mapping YAML)."""
from pyspark.sql import functions as F

LINEAGE_PASSTHROUGH = ["_source_system", "_source_object", "_source_file", "_batch_id", "_landing_batch_id", "_row_hash", "_ingest_ts"]


def fx_flatten(df):
    """FX envelopes (history + daily responses) -> one row per rate_date x quote currency, plus USD=1.0 for each date."""
    hist = "base string, rates map<string,map<string,double>>"
    daily = "base string, date string, rates map<string,double>"
    keep = [c for c in df.columns if c in LINEAGE_PASSTHROUGH or c in ("requested_date", "stale", "fetched_at_utc")]
    p = df.withColumn("_h", F.from_json("response_json", hist)).withColumn("_d", F.from_json("response_json", daily))
    h = (p.where(F.col("_h.rates").isNotNull()).select(*keep, F.col("_h.base").alias("base_currency"), F.explode("_h.rates").alias("rate_date", "_m"))
          .select(*keep, "base_currency", "rate_date", F.explode("_m").alias("quote_currency", "rate")))
    d = (p.where(F.col("_h.rates").isNull() & F.col("_d.rates").isNotNull())
          .select(*keep, F.col("_d.base").alias("base_currency"), F.col("_d.date").alias("rate_date"), F.explode("_d.rates").alias("quote_currency", "rate")))
    rates = h.unionByName(d)
    base = rates.select(*keep, "base_currency", "rate_date").dropDuplicates(["base_currency", "rate_date", "_source_file"]) \
                .withColumn("quote_currency", F.col("base_currency")).withColumn("rate", F.lit(1.0))
    return rates.unionByName(base).withColumn("stale", F.col("stale").cast("boolean"))


REGISTRY = {"fx_flatten": fx_flatten}
