#!/usr/bin/env python3
"""
Fraud detector MVP (rule-based)
Kafka payments -> rules -> PostgreSQL fraud_alerts + Kafka fraud-alerts
"""

import argparse
import json
import os
import sys
from collections import deque, defaultdict
from datetime import datetime, timedelta


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
try:
    import psycopg2  # type: ignore
except Exception:  # pragma: no cover - fallback for environments without psycopg2
    psycopg2 = None
    import pg8000  # type: ignore


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
    parser = argparse.ArgumentParser(description="Fraud detector MVP")
    parser.add_argument(
        "--payments-topic",
        default=None,
        help="Kafka payments topic (default from KAFKA_TOPIC_PAYMENTS)",
    )
    parser.add_argument(
        "--alerts-topic",
        default=None,
        help="Kafka fraud alerts topic (default from KAFKA_TOPIC_FRAUD_ALERTS)",
    )
    parser.add_argument(
        "--bootstrap",
        default=None,
        help="Kafka bootstrap servers (default from KAFKA_BOOTSTRAP_SERVERS)",
    )
    parser.add_argument(
        "--group-id",
        default="fraud-detector",
        help="Kafka consumer group id",
    )
    parser.add_argument(
        "--from-beginning",
        action="store_true",
        help="Consume from earliest offset (new group recommended)",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=0,
        help="Stop after N messages (0 = infinite)",
    )
    return parser.parse_args()


def parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    if "." in value:
        base, fraction = value.split(".", 1)
        fraction = (fraction + "000000")[:6]
        value = f"{base}.{fraction}"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def to_int_payment_id(payment_id: str | int | None) -> int | None:
    if payment_id is None:
        return None
    if isinstance(payment_id, int):
        return payment_id
    text = str(payment_id)
    if text.upper().startswith("PAY"):
        text = text[3:]
    try:
        return int(text)
    except ValueError:
        return None


def severity_from_score(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.7:
        return "medium"
    return "low"


def main() -> int:
    load_dotenv_if_available()
    args = parse_args()

    payments_topic = args.payments_topic or os.getenv("KAFKA_TOPIC_PAYMENTS", "payments")
    alerts_topic = args.alerts_topic or os.getenv("KAFKA_TOPIC_FRAUD_ALERTS", "fraud-alerts")
    bootstrap = args.bootstrap or os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092,localhost:9093,localhost:9094"
    )
    bootstrap_servers = [s.strip() for s in bootstrap.split(",") if s.strip()]

    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = int(os.getenv("POSTGRES_PORT", "5432"))
    pg_db = os.getenv("POSTGRES_DB", "kivendtout")
    pg_user = os.getenv("POSTGRES_USER", "postgres")
    pg_password = os.getenv("POSTGRES_PASSWORD", "postgres")

    if psycopg2 is not None:
        conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            dbname=pg_db,
            user=pg_user,
            password=pg_password,
        )
        conn.autocommit = True
    else:
        conn = pg8000.connect(
            host=pg_host,
            port=pg_port,
            database=pg_db,
            user=pg_user,
            password=pg_password,
        )
        conn.autocommit = True

    ensure_kafka_vendor_six()
    from kafka.consumer import KafkaConsumer
    from kafka.producer import KafkaProducer

    consumer = KafkaConsumer(
        payments_topic,
        bootstrap_servers=bootstrap_servers,
        group_id=args.group_id,
        enable_auto_commit=False,
        auto_offset_reset="earliest" if args.from_beginning else "latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        key_deserializer=lambda k: k.decode("utf-8") if k else None,
    )

    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
    )

    customer_country_cache: dict[str, str | None] = {}
    customer_first_purchase_cache: dict[str, bool] = {}

    # For velocity rule (per customer): timestamps deque
    velocity_window = timedelta(minutes=10)
    velocity_threshold = 5
    attempts_by_customer: dict[str, deque[datetime]] = defaultdict(deque)

    # For device change rule: store last device+ip per customer
    last_device_by_customer: dict[str, tuple[str | None, str | None, datetime]] = {}

    emitted_rules: set[tuple[int, str]] = set()

    rule_scores = {
        "high_amount": 0.85,
        "country_mismatch": 0.75,
        "velocity": 0.90,
        "device_change": 0.70,
        "time_anomaly": 0.60,
    }

    processed = 0

    try:
        for msg in consumer:
            data = msg.value
            processed += 1

            customer_id = data.get("customer_id")
            payment_id_raw = data.get("payment_id")
            payment_id = to_int_payment_id(payment_id_raw)
            amount = float(data.get("amount", 0) or 0)
            payment_country = data.get("payment_country")
            device_id = data.get("device_id")
            ip_hash = data.get("ip_hash")

            attempt_ts_raw = data.get("attempt_ts")
            attempt_ts = parse_timestamp(attempt_ts_raw) or datetime.utcnow()

            if customer_id and customer_id not in customer_country_cache:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT country FROM customers WHERE customer_id = %s", (customer_id,)
                    )
                    row = cur.fetchone()
                    customer_country_cache[customer_id] = row[0] if row else None

            if customer_id and customer_id not in customer_first_purchase_cache:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) FROM orders WHERE customer_id = %s", (customer_id,)
                    )
                    row = cur.fetchone()
                    customer_first_purchase_cache[customer_id] = (row[0] == 0) if row else True

            rules_triggered: list[str] = []

            # Rule 1: High amount + first purchase
            if amount > 100 and customer_id:
                if customer_first_purchase_cache.get(customer_id, False):
                    rules_triggered.append("high_amount")

            # Rule 2: Country mismatch
            if customer_id and payment_country:
                customer_country = customer_country_cache.get(customer_id)
                if customer_country and payment_country != customer_country:
                    rules_triggered.append("country_mismatch")

            # Rule 3: Velocity
            if customer_id:
                queue = attempts_by_customer[customer_id]
                queue.append(attempt_ts)
                while queue and attempt_ts - queue[0] > velocity_window:
                    queue.popleft()
                if len(queue) > velocity_threshold:
                    rules_triggered.append("velocity")

            # Rule 4: Device change within 1h
            if customer_id:
                last = last_device_by_customer.get(customer_id)
                if last:
                    last_device, last_ip, last_ts = last
                    if (device_id and last_device and device_id != last_device) and (
                        ip_hash and last_ip and ip_hash != last_ip
                    ):
                        if attempt_ts - last_ts <= timedelta(hours=1):
                            rules_triggered.append("device_change")
                last_device_by_customer[customer_id] = (device_id, ip_hash, attempt_ts)

            # Rule 5: Time anomaly (3h-6h)
            if 3 <= attempt_ts.hour <= 6:
                rules_triggered.append("time_anomaly")

            # Emit alerts
            for rule in rules_triggered:
                if payment_id is None:
                    continue
                key = (payment_id, rule)
                if key in emitted_rules:
                    continue
                emitted_rules.add(key)

                score = rule_scores.get(rule, 0.7)
                severity = severity_from_score(score)
                action_taken = "blocked" if severity == "high" else "reviewed"

                alert_doc = {
                    "payment_id": payment_id_raw,
                    "rule_triggered": rule,
                    "risk_score": score,
                    "severity": severity,
                    "alert_ts": attempt_ts.isoformat(),
                    "customer_id": customer_id,
                }

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO fraud_alerts (payment_id, alert_date, alert_type, risk_score, action_taken, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            payment_id,
                            attempt_ts,
                            rule,
                            score,
                            action_taken,
                            datetime.utcnow(),
                        ),
                    )

                producer.send(alerts_topic, value=alert_doc)

            consumer.commit()

            if args.max_messages and processed >= args.max_messages:
                break

    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()
        producer.flush()
        producer.close()
        conn.close()

    print(f"Processed {processed} payment events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
