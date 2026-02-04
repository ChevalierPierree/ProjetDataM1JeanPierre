#!/bin/bash

set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

print_section() {
  echo ""
  echo "== $1 =="
}

print_section "Environment"
if [ -f "${ENV_FILE}" ]; then
  echo "Found .env at ${ENV_FILE}"
  set -a
  # shellcheck source=/dev/null
  . "${ENV_FILE}"
  set +a
else
  echo "No .env found at ${ENV_FILE}"
fi

MONGO_URI_VALUE="${MONGO_URI:-}"
MONGO_DB_VALUE="${MONGO_DB:-}"

if [ -z "${MONGO_URI_VALUE}" ]; then
  MONGO_HOST_VALUE="${MONGODB_HOST:-localhost}"
  MONGO_PORT_VALUE="${MONGODB_PORT:-27017}"
  MONGO_USER_VALUE="${MONGODB_USER:-admin}"
  MONGO_PASSWORD_VALUE="${MONGODB_PASSWORD:-admin}"
  MONGO_DB_VALUE="${MONGO_DB_VALUE:-${MONGODB_DB:-kivendtout}}"
  MONGO_URI_VALUE="mongodb://${MONGO_USER_VALUE}:${MONGO_PASSWORD_VALUE}@${MONGO_HOST_VALUE}:${MONGO_PORT_VALUE}/?authSource=admin"
fi

MONGO_DB_VALUE="${MONGO_DB_VALUE:-kivendtout}"

print_section "MongoDB URI"
echo "MONGO_URI=${MONGO_URI_VALUE}"
echo "MONGO_DB=${MONGO_DB_VALUE}"

print_section "Port Check (27017)"
if command -v lsof >/dev/null 2>&1; then
  lsof -i :27017 || echo "No process is listening on 27017"
elif command -v nc >/dev/null 2>&1; then
  nc -zv localhost 27017 || echo "Port 27017 is not reachable"
else
  echo "No lsof or nc available to check the port."
fi

print_section "Docker Compose"
if command -v docker >/dev/null 2>&1; then
  if docker compose ps >/dev/null 2>&1; then
    docker compose ps
  else
    echo "Cannot access Docker daemon. Is Docker running?"
  fi
else
  echo "Docker not installed or not in PATH."
fi

print_section "MongoDB Ping"
if command -v mongosh >/dev/null 2>&1; then
  mongosh "${MONGO_URI_VALUE}" --eval "db.runCommand({ ping: 1 })" || \
    echo "Authentication failed or MongoDB not reachable."
else
  echo "mongosh not installed. Install it or use a GUI client."
fi

print_section "Next Steps"
echo "- If authentication fails, verify MongoDB credentials in .env."
echo "- If Docker is used, ensure kivendtout-mongodb is Up."
echo "- If a local mongod is running, it may shadow the Docker instance."
