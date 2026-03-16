# Checklist Soutenance - Sujet 1 (KiVendTout)

## Objectif
Valider les 11 exigences du sujet 1 avec des preuves exécutables et reproductibles.

## Tâches à exécuter
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

## Commandes
```bash
./.venv/bin/python scripts/train_id_card_fingerprint_model.py
bash scripts/snapshot_raw_data_to_minio.sh
./.venv/bin/python scripts/data_quality_checks.py
./.venv/bin/python scripts/validate_sujet1_soutenance.py
```

## Preuves générées
- `models/id_card_fingerprint_model.json`
- `logs/id_card_model_report.json`
- `logs/data_lake_snapshot_*.json`
- `logs/data_quality_report.json`
- `logs/sujet1_validation_report.json`
