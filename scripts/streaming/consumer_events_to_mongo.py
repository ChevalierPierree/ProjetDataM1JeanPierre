#!/usr/bin/env python3
"""
Consumer Kafka -> MongoDB
Lit le topic user-events et insere les documents dans la collection events.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from kafka import KafkaConsumer
from pymongo import MongoClient
from pymongo.errors import BulkWriteError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kafka consumer to MongoDB")
    parser.add_argument(
        "--topic",
        default=None,
        help="Kafka topic (default from KAFKA_TOPIC_USER_EVENTS)",
    )
    parser.add_argument(
        "--bootstrap",
        default=None,
        help="Kafka bootstrap servers (default from KAFKA_BOOTSTRAP_SERVERS)",
    )
    parser.add_argument(
        "--group-id",
        default="events-to-mongo",
        help="Kafka consumer group id",
    )
    parser.add_argument(
        "--from-beginning",
        action="store_true",
        help="Consume from earliest offset (new group recommended)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="MongoDB insert batch size",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=0,
        help="Stop after N messages (0 = infinite)",
    )
    parser.add_argument(
        "--mongo-uri",
        default=None,
        help="MongoDB URI (override .env)",
    )
    parser.add_argument(
        "--mongo-db",
        default=None,
        help="MongoDB database name (override .env)",
    )
    parser.add_argument(
        "--mongo-collection",
        default=None,
        help="MongoDB collection name (override .env)",
    )
    return parser.parse_args()


def parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    # Example: 2025-11-19 14:31:02.594554442 (9 digits)
    if "." in value:
        base, fraction = value.split(".", 1)
        fraction = (fraction + "000000")[:6]
        value = f"{base}.{fraction}"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def ensure_indexes(collection) -> None:
    collection.create_index("customer_id")
    collection.create_index("session_id")
    collection.create_index("event_type")
    # TTL index: keep 2 years
    collection.create_index("ts", expireAfterSeconds=60 * 60 * 24 * 365 * 2)


def main() -> int:
    load_dotenv()
    args = parse_args()

    topic = args.topic or os.getenv("KAFKA_TOPIC_USER_EVENTS", "user-events")
    bootstrap = args.bootstrap or os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092,localhost:9093,localhost:9094"
    )
    bootstrap_servers = [s.strip() for s in bootstrap.split(",") if s.strip()]

    mongo_uri = args.mongo_uri or os.getenv("MONGO_URI")
    mongo_db = args.mongo_db or os.getenv("MONGO_DB")
    mongo_collection = args.mongo_collection or os.getenv("MONGO_COLLECTION", "events")

    if not mongo_uri:
        mongo_host = os.getenv("MONGODB_HOST", "localhost")
        mongo_port = int(os.getenv("MONGODB_PORT", "27017"))
        mongo_user = os.getenv("MONGODB_USER", "admin")
        mongo_password = os.getenv("MONGODB_PASSWORD", "admin")
        mongo_uri = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}"

    if not mongo_db:
        mongo_db = os.getenv("MONGODB_DB", "kivendtout")

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)

    try:
        client.admin.command("ping")
    except Exception as exc:
        print("MongoDB connection failed.")
        print(f"URI used: {mongo_uri}")
        print("Check that MongoDB is running and credentials match .env.")
        print(f"Original error: {exc}")
        return 1
    collection = client[mongo_db][mongo_collection]

    ensure_indexes(collection)

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id=args.group_id,
        enable_auto_commit=False,
        auto_offset_reset="earliest" if args.from_beginning else "latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        key_deserializer=lambda k: k.decode("utf-8") if k else None,
    )

    batch = []
    total = 0

    try:
        for message in consumer:
            doc = message.value

            # Normalize timestamps
            raw_ts = doc.get("ts")
            parsed_ts = parse_timestamp(raw_ts) if isinstance(raw_ts, str) else None
            if parsed_ts:
                doc["ts_raw"] = raw_ts
                doc["ts"] = parsed_ts

            # Use event_id as Mongo _id for idempotency
            if "event_id" in doc:
                doc["_id"] = doc["event_id"]

            batch.append(doc)
            total += 1

            if len(batch) >= args.batch_size:
                try:
                    collection.insert_many(batch, ordered=False)
                except BulkWriteError:
                    # Ignore duplicate key errors
                    pass
                consumer.commit()
                batch = []

            if args.max_messages and total >= args.max_messages:
                break

    except KeyboardInterrupt:
        pass
    finally:
        if batch:
            try:
                collection.insert_many(batch, ordered=False)
            except BulkWriteError:
                pass
            consumer.commit()

        consumer.close()
        client.close()

    print(f"Consumed {total} messages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
