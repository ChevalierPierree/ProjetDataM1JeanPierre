#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATASET_DIR="${ROOT_DIR}/kivendtout_dataset"
TIMESTAMP_UTC="$(date -u +"%Y%m%dT%H%M%SZ")"
SNAPSHOT_PREFIX="bronze/raw_snapshot/${TIMESTAMP_UTC}"
LOG_DIR="${ROOT_DIR}/logs"
MANIFEST_TSV="$(mktemp)"
MANIFEST_JSON="${LOG_DIR}/data_lake_snapshot_${TIMESTAMP_UTC}.json"

MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minio}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minio123}"

mkdir -p "${LOG_DIR}"

echo "=== SNAPSHOT RAW DATA -> MINIO ==="
echo "Dataset dir   : ${DATASET_DIR}"
echo "Snapshot UTC  : ${TIMESTAMP_UTC}"
echo "MinIO endpoint: ${MINIO_ENDPOINT}"

if [[ ! -d "${DATASET_DIR}" ]]; then
  echo "ERREUR: dataset introuvable: ${DATASET_DIR}" >&2
  exit 1
fi

# Prépare l'alias et le bucket cible.
docker compose exec -T minio /bin/sh -c \
  "export LC_ALL=C LANG=C; mc alias set local ${MINIO_ENDPOINT} ${MINIO_ACCESS_KEY} ${MINIO_SECRET_KEY} >/dev/null; mc mb --ignore-existing local/bronze >/dev/null"

FILES=()
while IFS= read -r file; do
  FILES+=("${file}")
done < <(
  {
    find "${DATASET_DIR}" -maxdepth 1 -type f \( -name "*.csv" -o -name "*.parquet" -o -name "*.jsonl" \)
    find "${DATASET_DIR}/synthetic_id_cards" -maxdepth 1 -type f -name "*.png"
  } | sort
)

if [[ "${#FILES[@]}" -eq 0 ]]; then
  echo "ERREUR: aucun fichier à uploader" >&2
  exit 1
fi

uploaded=0
for file in "${FILES[@]}"; do
  rel_path="${file#${ROOT_DIR}/}"
  object_path="${SNAPSHOT_PREFIX}/${rel_path}"
  sha256="$(shasum -a 256 "${file}" | awk '{print $1}')"
  size_bytes="$(wc -c < "${file}" | tr -d ' ')"

  cat "${file}" | docker compose exec -T minio /bin/sh -c \
    "export LC_ALL=C LANG=C; mc alias set local ${MINIO_ENDPOINT} ${MINIO_ACCESS_KEY} ${MINIO_SECRET_KEY} >/dev/null; mc pipe \"local/${object_path}\" >/dev/null"

  printf "%s\t%s\t%s\t%s\n" "${rel_path}" "${object_path}" "${sha256}" "${size_bytes}" >> "${MANIFEST_TSV}"
  uploaded=$((uploaded + 1))
done

python3 - "${MANIFEST_TSV}" "${MANIFEST_JSON}" "${TIMESTAMP_UTC}" "${uploaded}" <<'PY'
import json
import sys
from pathlib import Path

manifest_tsv = Path(sys.argv[1])
manifest_json = Path(sys.argv[2])
timestamp_utc = sys.argv[3]
uploaded = int(sys.argv[4])

files = []
total_bytes = 0
for line in manifest_tsv.read_text(encoding="utf-8").splitlines():
    rel_path, object_path, sha256, size_bytes = line.split("\t")
    size_int = int(size_bytes)
    total_bytes += size_int
    files.append(
        {
            "relative_path": rel_path,
            "object_path": object_path,
            "sha256": sha256,
            "size_bytes": size_int,
        }
    )

payload = {
    "snapshot_utc": timestamp_utc,
    "uploaded_files": uploaded,
    "total_bytes": total_bytes,
    "files": files,
}
manifest_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(str(manifest_json))
PY

rm -f "${MANIFEST_TSV}"

echo "Upload terminé: ${uploaded} fichiers"
echo "Manifest       : ${MANIFEST_JSON}"
