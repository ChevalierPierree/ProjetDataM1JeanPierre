#!/usr/bin/env python3
"""
Producer Kafka - KiVendTout
Publie les evenements du fichier events.jsonl vers le topic user-events.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from kafka import KafkaProducer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kafka producer for events.jsonl")
    parser.add_argument(
        "--file",
        default="kivendtout_dataset/events.jsonl",
        help="Path to events.jsonl",
    )
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
        "--max-per-second",
        type=float,
        default=0.0,
        help="Throttle rate (0 = no throttle)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max number of events to send (0 = all)",
    )
    parser.add_argument(
        "--flush-every",
        type=int,
        default=1000,
        help="Flush producer every N messages",
    )
    parser.add_argument(
        "--acks",
        default="all",
        help="Kafka acks (0, 1, all). Default: all",
    )
    parser.add_argument(
        "--print-every",
        type=int,
        default=5000,
        help="Print progress every N messages",
    )
    return parser.parse_args()


def read_events(file_path: Path):
    with file_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                yield None, line
                continue
            yield payload, line


def main() -> int:
    load_dotenv()
    args = parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return 1

    topic = args.topic or os.getenv("KAFKA_TOPIC_USER_EVENTS", "user-events")
    bootstrap = args.bootstrap or os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092,localhost:9093,localhost:9094"
    )
    bootstrap_servers = [s.strip() for s in bootstrap.split(",") if s.strip()]

    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        acks=args.acks,
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        value_serializer=lambda v: v.encode("utf-8"),
        linger_ms=50,
        retries=5,
    )

    total = 0
    errors = 0
    start_time = time.time()

    throttle_delay = 0.0
    if args.max_per_second and args.max_per_second > 0:
        throttle_delay = 1.0 / args.max_per_second

    for payload, raw_line in read_events(file_path):
        if payload is None:
            errors += 1
            continue

        key = payload.get("customer_id") or payload.get("session_id") or payload.get("event_id")
        producer.send(topic, key=key, value=raw_line)
        total += 1

        if args.flush_every and total % args.flush_every == 0:
            producer.flush()

        if args.print_every and total % args.print_every == 0:
            elapsed = time.time() - start_time
            rate = total / elapsed if elapsed > 0 else 0
            print(f"Sent {total} events (errors: {errors}) - {rate:.1f} msg/s")

        if throttle_delay > 0:
            time.sleep(throttle_delay)

        if args.limit and total >= args.limit:
            break

    producer.flush()
    elapsed = time.time() - start_time
    rate = total / elapsed if elapsed > 0 else 0

    print("Done.")
    print(f"Total sent: {total}")
    print(f"Errors: {errors}")
    print(f"Elapsed: {elapsed:.2f}s")
    print(f"Rate: {rate:.1f} msg/s")

    return 0


if __name__ == "__main__":
    sys.exit(main())
