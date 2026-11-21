"""Landing for the event stream: Event Hubs (Kafka endpoint) -> raw JSON envelope files in landing (replayable)."""
import datetime as dt

from pyspark.sql import functions as F

from edap_framework.core import audit, config, spark_utils


def land_events(spark, spec, env, namespace, batch_id=None, scenario=None):
    batch_id = batch_id or audit.new_batch_id()
    started = dt.datetime.utcnow()
    s, tgt = spec["source"], spec["target"]
    conn = spark_utils.secret(spark, env, s["secret_key"])
    jaas = ('kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule required '
            'username="$ConnectionString" password="%s";' % conn)
    stream = (spark.readStream.format("kafka")
              .option("kafka.bootstrap.servers", s["kafka_bootstrap"].format(eventhub_namespace=namespace))
              .option("subscribe", s["topic"])
              .option("kafka.security.protocol", "SASL_SSL")
              .option("kafka.sasl.mechanism", "PLAIN")
              .option("kafka.sasl.jaas.config", jaas)
              .option("startingOffsets", s["starting_offsets"])
              .option("maxOffsetsPerTrigger", str(s["max_offsets_per_trigger"]))
              .option("failOnDataLoss", "false")
              .load()
              .select(F.col("key").cast("string").alias("key"), F.col("value").cast("string").alias("value"),
                      "topic", "partition", "offset", "timestamp")
              .withColumn("ingest_date", F.current_date())
              .withColumn("batch_id", F.lit(batch_id)))
    q = (stream.writeStream.format(tgt["format"]).outputMode("append").partitionBy("ingest_date", "batch_id")
         .option("checkpointLocation", config.storage_uri(env, spec["checkpoint"]["container"], spec["checkpoint"]["path"]))
         .trigger(availableNow=True)
         .start(config.storage_uri(env, tgt["container"], tgt["path"])))
    q.awaitTermination()
    n = sum(p.get("numOutputRows", 0) for p in [q.lastProgress or {}])
    audit.log_run(spark, spec["audit"]["run_log"], batch_id=batch_id, layer="landing", source_system=spec["source_system"],
                  table_name=spec["table"], scenario=scenario, status="SUCCESS", rows_processed=n, started_ts=started,
                  finished_ts=dt.datetime.utcnow(), details="availableNow drain of %s" % s["topic"])
    return n
