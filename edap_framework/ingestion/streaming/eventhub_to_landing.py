"""Landing for the event stream, as small functions: build_event_stream -> write_event_stream."""
from pyspark.sql import functions as F

from edap_framework.core import config, spark_utils


def build_event_stream(spark, spec, env, namespace, batch_id):
    s = spec["source"]
    jaas = ('kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule required '
            'username="$ConnectionString" password="%s";' % spark_utils.secret(spark, env, s["secret_key"]))
    return (spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", s["kafka_bootstrap"].format(eventhub_namespace=namespace))
            .option("subscribe", s["topic"]).option("kafka.security.protocol", "SASL_SSL").option("kafka.sasl.mechanism", "PLAIN")
            .option("kafka.sasl.jaas.config", jaas).option("startingOffsets", s["starting_offsets"])
            .option("maxOffsetsPerTrigger", str(s["max_offsets_per_trigger"])).option("failOnDataLoss", "false").load()
            .select(F.col("key").cast("string").alias("key"), F.col("value").cast("string").alias("value"), "topic", "partition", "offset", "timestamp")
            .withColumn("ingest_date", F.current_date()).withColumn("batch_id", F.lit(batch_id)))


def write_event_stream(spark, spec, env, df, batch_id, adhoc=False):
    """Drain what is in the hub (availableNow). Adhoc = replay from the earliest offset with a throw-away checkpoint."""
    tgt, cp = spec["target"], spec["checkpoint"]
    cp_path = cp["path"] + ("_adhoc_%s" % batch_id if adhoc else "")
    q = (df.writeStream.format(tgt["format"]).outputMode("append").partitionBy("ingest_date", "batch_id")
         .option("checkpointLocation", config.storage_uri(env, cp["container"], cp_path)).trigger(availableNow=True)
         .start(config.storage_uri(env, tgt["container"], tgt["path"])))
    q.awaitTermination()
    return sum((q.lastProgress or {}).get("numInputRows", 0) for _ in [0])
