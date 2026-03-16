# Checklist Soutenance - Sujet 1 (KiVendTout)

## Objectif
Valider les 11 exigences du sujet 1 et les compléments "conformité parfaite" avec preuves exécutables et reproductibles.

## Tâches à exécuter (Sujet 1)
1. **Sécuriser l’API**
   - API key optionnelle via `API_KEY_REQUIRED`, `API_KEY_HEADER`, `API_KEY_VALUE`.
   - Hachage `SHA-256` du `document_number` côté `POST /api/verify-id`.
2. **Activer la reconnaissance CNI**
   - Entraîner le modèle empreinte image: `scripts/train_id_card_fingerprint_model.py`.
   - Intégrer l’inférence dans l’API avec fallback labels.
3. **Centraliser les données brutes avec historisation**
   - Snapshot horodaté vers MinIO bronze via `scripts/snapshot_raw_data_to_minio.sh`.
4. **Mesurer la qualité des données**
   - Exécuter `scripts/data_quality_checks.py` (PostgreSQL + MongoDB).
5. **Valider le sujet 1 bout en bout**
   - Exécuter `scripts/validate_sujet1_soutenance.py`.
   - Consulter `logs/sujet1_validation_report.json`.

## Tâches à exécuter (Conformité parfaite)
1. **RBAC + quotas API**
   - Contrôle rôles/permissions + rate limit glissant par clé/utilisateur.
   - Test formalisé: `scripts/test_api_rbac_rate_limit.py`.
2. **Sécurité Data Lake MinIO**
   - Comptes dédiés + policies: `security/minio/policies/*.json`.
   - Rotation secrets: `scripts/rotate_minio_credentials.sh`.
   - TLS: `scripts/generate_minio_tls_certs.sh`.
3. **Flux micro-batch**
   - Pipeline MongoDB -> PostgreSQL: `scripts/micro_batch_events_to_postgres.py`.
   - API de suivi: `GET /api/micro-batch/stats`.
4. **Tests charge DB + résilience/failover**
   - Charge DB: `scripts/test_db_load.py`.
   - Résilience: `scripts/test_resilience_failover.py`.
5. **KPI transfert standardisés**
   - Historique KPI: `logs/transfer_kpi_history.jsonl`.
   - API KPI: `GET /api/transfer/kpis`.
   - Dashboard: `dashboard/transfer_kpi_dashboard.html`.
6. **Validation globale conformité**
   - Exécuter `scripts/validate_perfect_compliance.py`.
   - Consulter `logs/perfect_compliance_report.json`.

## Commandes
```bash
./.venv/bin/python scripts/train_id_card_fingerprint_model.py
bash scripts/snapshot_raw_data_to_minio.sh
./.venv/bin/python scripts/data_quality_checks.py
./.venv/bin/python scripts/validate_sujet1_soutenance.py

# Conformité parfaite
./.venv/bin/python scripts/test_api_rbac_rate_limit.py
bash scripts/generate_minio_tls_certs.sh
bash scripts/rotate_minio_credentials.sh all
./.venv/bin/python scripts/micro_batch_events_to_postgres.py --run-once --window-seconds 30
./.venv/bin/python scripts/test_db_load.py --pg-requests 120 --mongo-requests 120 --concurrency 12
./.venv/bin/python scripts/test_resilience_failover.py --service postgres --dry-run
./.venv/bin/python scripts/validate_perfect_compliance.py

# Cleaning artefacts runtime
bash scripts/clean_project_artifacts.sh
```

## Preuves générées
- `models/id_card_fingerprint_model.json`
- `logs/id_card_model_report.json`
- `logs/data_lake_snapshot_*.json`
- `logs/data_quality_report.json`
- `logs/sujet1_validation_report.json`
- `logs/api_rbac_rate_limit_report.json`
- `logs/db_load_test_report.json`
- `logs/resilience_failover_report.json`
- `logs/transfer_kpi_history.jsonl`
- `logs/perfect_compliance_report.json`
