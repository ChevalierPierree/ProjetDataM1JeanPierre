#!/usr/bin/env python3
"""
Producer Kafka - Paiements KiVendTout
Publie les lignes du fichier payments.csv vers le topic payments.
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path


def load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv as _load_dotenv
    except Exception:
        try:
            import dotenv as _dotenv  # type: ignore

            _load_dotenv = getattr(_dotenv, "load_dotenv", None)
        except Exception:
            _load_dotenv = None

    if _load_dotenv is None:
        print(
            "Warning: python-dotenv not available. Proceeding without loading .env.",
            file=sys.stderr,
        )
        return

    _load_dotenv()


def ensure_kafka_vendor_six() -> None:
    """Patch kafka.vendor.six when kafka-python is missing vendored six."""
    try:
        import kafka.vendor.six  # type: ignore  # noqa: F401
        return
    except Exception:
        pass

    try:
        import six  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "Missing dependency 'six'. Install it with: python3 -m pip install six"
        ) from exc

    import sys
    import types

    vendor_module = types.ModuleType("kafka.vendor")
    vendor_module.six = six  # type: ignore[attr-defined]
    sys.modules.setdefault("kafka.vendor", vendor_module)
    sys.modules["kafka.vendor.six"] = six

    # Ensure kafka.admin.KafkaAdminClient exists (broken kafka-python package on some envs)
    admin_module = sys.modules.get("kafka.admin")
    if admin_module is None:
        admin_module = types.ModuleType("kafka.admin")
        sys.modules["kafka.admin"] = admin_module
    if not hasattr(admin_module, "KafkaAdminClient"):
        class KafkaAdminClient:  # pylint: disable=too-few-public-methods
            pass

        admin_module.KafkaAdminClient = KafkaAdminClient  # type: ignore[attr-defined]

    # Provide a minimal kafka.metrics.stats module if missing
    try:
        import kafka.metrics  # type: ignore  # noqa: F401
        import kafka.metrics.stats  # type: ignore  # noqa: F401
    except Exception:
        metrics_pkg = sys.modules.get("kafka.metrics")
        if metrics_pkg is None:
            metrics_pkg = types.ModuleType("kafka.metrics")
            metrics_pkg.__path__ = []  # mark as package
            sys.modules["kafka.metrics"] = metrics_pkg

        class MetricConfig:  # pylint: disable=too-few-public-methods
            def __init__(self, *args, **kwargs):
                pass

        class KafkaMetric:  # pylint: disable=too-few-public-methods
            def __init__(self, *args, **kwargs):
                pass

        class MetricName:  # pylint: disable=too-few-public-methods
            def __init__(self, *args, **kwargs):
                pass

        class AnonMeasurable:  # pylint: disable=too-few-public-methods
            def __init__(self, func):
                self.func = func

        class Sensor:  # pylint: disable=too-few-public-methods
            def add(self, *args, **kwargs):
                return None

            def record(self, *args, **kwargs):
                return None

        class Metrics:  # pylint: disable=too-few-public-methods
            def __init__(self, *args, **kwargs):
                self._sensors = {}

            def sensor(self, name, *args, **kwargs):
                sensor = self._sensors.get(name)
                if sensor is None:
                    sensor = Sensor()
                    self._sensors[name] = sensor
                return sensor

            def get_sensor(self, name):
                return self._sensors.get(name)

            def add_metric(self, *args, **kwargs):
                return None

            def metric_name(self, name, *args, **kwargs):
                return name

        metrics_pkg.MetricConfig = MetricConfig
        metrics_pkg.Metrics = Metrics
        metrics_pkg.AnonMeasurable = AnonMeasurable
        metrics_pkg.MetricName = MetricName
        metrics_pkg.KafkaMetric = KafkaMetric

        measurable_mod = types.ModuleType("kafka.metrics.measurable")
        measurable_mod.AnonMeasurable = AnonMeasurable
        sys.modules["kafka.metrics.measurable"] = measurable_mod

        stats_mod = types.ModuleType("kafka.metrics.stats")

        class Avg:  # pylint: disable=too-few-public-methods
            def __init__(self, *args, **kwargs):
                pass

        class Count:  # pylint: disable=too-few-public-methods
            def __init__(self, *args, **kwargs):
                pass

        class Max:  # pylint: disable=too-few-public-methods
            def __init__(self, *args, **kwargs):
                pass

        class Rate:  # pylint: disable=too-few-public-methods
            def __init__(self, *args, **kwargs):
                pass

        stats_mod.Avg = Avg
        stats_mod.Count = Count
        stats_mod.Max = Max
        stats_mod.Rate = Rate
        sys.modules["kafka.metrics.stats"] = stats_mod

        rate_mod = types.ModuleType("kafka.metrics.stats.rate")

        class TimeUnit:  # pylint: disable=too-few-public-methods
            NANOSECONDS = "nanoseconds"
            MILLISECONDS = "milliseconds"
            SECONDS = "seconds"

        rate_mod.TimeUnit = TimeUnit
        sys.modules["kafka.metrics.stats.rate"] = rate_mod


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kafka producer for payments.csv")
    parser.add_argument(
        "--file",
        default="kivendtout_dataset/payments.csv",
        help="Path to payments.csv",
    )
    parser.add_argument(
        "--topic",
        default=None,
        help="Kafka topic (default from KAFKA_TOPIC_PAYMENTS)",
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
        default=500,
        help="Flush producer every N messages",
    )
    parser.add_argument(
        "--acks",
        default="all",
        help="Kafka acks (0, 1, all). Default: all",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv_if_available()
    args = parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return 1

    topic = args.topic or os.getenv("KAFKA_TOPIC_PAYMENTS", "payments")
    bootstrap = args.bootstrap or os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092,localhost:9093,localhost:9094"
    )
    bootstrap_servers = [s.strip() for s in bootstrap.split(",") if s.strip()]

    ensure_kafka_vendor_six()
    from kafka.producer import KafkaProducer

    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        acks=args.acks,
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        linger_ms=50,
        retries=5,
    )

    total = 0
    start_time = time.time()

    throttle_delay = 0.0
    if args.max_per_second and args.max_per_second > 0:
        throttle_delay = 1.0 / args.max_per_second

    with file_path.open("r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Keep raw fields; consumer will parse types
            key = row.get("customer_id") or row.get("payment_id")
            producer.send(topic, key=key, value=row)
            total += 1

            if args.flush_every and total % args.flush_every == 0:
                producer.flush()

            if throttle_delay > 0:
                time.sleep(throttle_delay)

            if args.limit and total >= args.limit:
                break

    producer.flush()
    elapsed = time.time() - start_time
    rate = total / elapsed if elapsed > 0 else 0

    print("Done.")
    print(f"Total sent: {total}")
    print(f"Elapsed: {elapsed:.2f}s")
    print(f"Rate: {rate:.1f} msg/s")

    return 0


if __name__ == "__main__":
    sys.exit(main())
