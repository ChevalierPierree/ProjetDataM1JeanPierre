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
SQL_FILE="${ROOT_DIR}/scripts/postgres/validate.sql"

if [ ! -f "${SQL_FILE}" ]; then
  echo "Missing SQL file: ${SQL_FILE}"
  exit 1
fi

echo "Running validation on ${CONTAINER} (${DB})"

cat "${SQL_FILE}" | docker exec -i -e PGPASSWORD="${PASSWORD}" "${CONTAINER}" \
  psql -U "${USER}" -d "${DB}" -v ON_ERROR_STOP=1 -f /dev/stdin
