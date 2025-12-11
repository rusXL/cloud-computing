import os
import json
import logging
from kafka import KafkaConsumer
from pymongo.database import Database
from shared.mongo import get_collection_by_type, get_db

# Logging
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

# Config
KAFKA = os.environ.get("KAFKA", "localhost:9093")
TOPICS = ["potato", "tomato", "pepper"]
GROUP_ID = "consumers"


# Lifespan
def main():
    # Mongo
    logger.info("Connecting to Mongo")
    db = get_db()

    # Kafka
    logger.info("Connecting to Kafka")
    consumer = KafkaConsumer(
        *TOPICS,
        bootstrap_servers=KAFKA,
        group_id=GROUP_ID,
        auto_offset_reset="earliest",  # when there’s no committed offset yet
        enable_auto_commit=False,
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    )

    logger.info("Kafka consumer started")
    consume_messages(consumer, db)


# Consumer loop
def consume_messages(consumer: KafkaConsumer, db: Database):
    for m in consumer:
        try:
            value, topic = m.value, m.topic

            collection = get_collection_by_type(db, topic)

            result = collection.update_one(
                {"id": value["id"]}, {"$set": value}, upsert=True
            )

            if result.upserted_id:
                logger.info(f"🟢 Inserted {topic} #{value['id']}")
            elif result.modified_count > 0:
                logger.info(f"🟡 Updated {topic} #{value['id']}")
            else:
                logger.info(f"🔴 No changes {topic} #{value['id']}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
        finally:
            consumer.commit()


if __name__ == "__main__":
    main()
