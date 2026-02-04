#!/bin/bash

set -euo pipefail

# Create Kafka topics for KiVendTout streaming MVP
# This script runs kafka-topics inside the kafka-1 container.

BROKER="kafka-1:19092"
PARTITIONS=3
REPLICATION=3

TOPICS=(
  "user-events"
  "payments"
  "orders"
  "cart-events"
  "fraud-alerts"
)

echo "Creating Kafka topics on ${BROKER}..."

for topic in "${TOPICS[@]}"; do
  echo "- ${topic}"
  docker exec kivendtout-kafka-1 kafka-topics \
    --bootstrap-server "${BROKER}" \
    --create \
    --if-not-exists \
    --partitions "${PARTITIONS}" \
    --replication-factor "${REPLICATION}" \
    --topic "${topic}"
done

echo "Done. Listing topics:"
docker exec kivendtout-kafka-1 kafka-topics --bootstrap-server "${BROKER}" --list
