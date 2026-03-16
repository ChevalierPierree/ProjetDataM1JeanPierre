#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "ERREUR: python virtuel introuvable: ${PYTHON_BIN}" >&2
  exit 1
fi

RUN_FAILOVER="${RUN_FAILOVER:-false}"

echo "=== RUN PERFECT COMPLIANCE ==="
echo "Root         : ${ROOT_DIR}"
echo "Python       : ${PYTHON_BIN}"
echo "Run failover : ${RUN_FAILOVER}"
echo

echo "[1/8] RBAC + quotas API"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/test_api_rbac_rate_limit.py"

echo "[2/8] Génération cert TLS MinIO"
bash "${ROOT_DIR}/scripts/generate_minio_tls_certs.sh"

echo "[3/8] Snapshot Data Lake (compte bronze-writer)"
bash "${ROOT_DIR}/scripts/snapshot_raw_data_to_minio.sh"

echo "[4/8] Flux micro-batch (1 fenêtre)"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/micro_batch_events_to_postgres.py" --run-once --window-seconds 30

echo "[5/8] Tests charge DB"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/test_db_load.py" --pg-requests 120 --mongo-requests 120 --concurrency 12

echo "[6/8] Tests résilience"
if [[ "${RUN_FAILOVER}" == "true" ]]; then
  "${PYTHON_BIN}" "${ROOT_DIR}/scripts/test_resilience_failover.py" --service postgres
else
  "${PYTHON_BIN}" "${ROOT_DIR}/scripts/test_resilience_failover.py" --service postgres --dry-run
fi

echo "[7/8] Validation sujet 1"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/validate_sujet1_soutenance.py"

echo "[8/8] Validation conformité parfaite"
if [[ "${RUN_FAILOVER}" == "true" ]]; then
  "${PYTHON_BIN}" "${ROOT_DIR}/scripts/validate_perfect_compliance.py" --run-failover
else
  "${PYTHON_BIN}" "${ROOT_DIR}/scripts/validate_perfect_compliance.py"
fi

echo
echo "Terminé. Rapports:"
echo " - logs/sujet1_validation_report.json"
echo " - logs/perfect_compliance_report.json"
echo " - logs/api_rbac_rate_limit_report.json"
echo " - logs/db_load_test_report.json"
echo " - logs/resilience_failover_report.json"
echo " - logs/transfer_kpi_history.jsonl"
