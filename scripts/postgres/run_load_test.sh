#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

if [ -f "${ENV_FILE}" ]; then
  set -a
  # shellcheck source=/dev/null
  . "${ENV_FILE}"
  set +a
fi

CONTAINER="${POSTGRES_CONTAINER:-kivendtout-postgres}"
DB="${POSTGRES_DB:-kivendtout}"
USER="${POSTGRES_USER:-postgres}"
PASSWORD="${POSTGRES_PASSWORD:-postgres}"
DURATION="${PG_BENCH_DURATION:-30}"
CLIENTS="${PG_BENCH_CLIENTS:-10}"
THREADS="${PG_BENCH_THREADS:-2}"
SQL_FILE="${ROOT_DIR}/scripts/postgres/pgbench_readonly.sql"

if [ ! -f "${SQL_FILE}" ]; then
  echo "Missing pgbench script: ${SQL_FILE}"
  exit 1
fi

echo "Running pgbench load test on ${CONTAINER} (${DB})"
echo "Duration: ${DURATION}s | Clients: ${CLIENTS} | Threads: ${THREADS}"

auth_env=(-e PGPASSWORD="${PASSWORD}")

cat "${SQL_FILE}" | docker exec -i "${auth_env[@]}" "${CONTAINER}" \
  pgbench -U "${USER}" -d "${DB}" -n -T "${DURATION}" -c "${CLIENTS}" -j "${THREADS}" -f /dev/stdin
