# KiVendTout

Plateforme data pour e-commerce avec detection de fraude, controle d'identite, supervision temps reel et pipelines de transfert.

## Vue d'ensemble

Le projet couvre quatre besoins operationnels:
- detection de fraude et traitement des alertes,
- blocage des commandes 18+ pour les mineurs,
- historisation et transfert des donnees,
- outillage de validation, charge et resilience.

Le socle technique repose sur PostgreSQL, MongoDB, Kafka, MinIO, FastAPI et un front de supervision sur `7600`.

## Demarrage rapide

### Methode automatisee

```bash
cd /Users/jeanmacario/Documents/GitHub/ProjetDataM1JeanPierre
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.patator.txt
./patator
```

### Methode de verification recommandee

```bash
cd /Users/jeanmacario/Documents/GitHub/ProjetDataM1JeanPierre
source .venv/bin/activate
bash scripts/checklist_and_launch.sh
```

## Commandes utiles

### Validation globale

```bash
./.venv/bin/python scripts/validate_sujet1.py
./.venv/bin/python scripts/validate_perfect_compliance.py
./.venv/bin/python scripts/data_quality_checks.py
```

### Demonstrations metier

```bash
bash scripts/test_use_cases.sh
bash scripts/run_micro_batch.sh once
bash scripts/test_alert_notifications.sh
curl -X POST http://localhost:8000/api/data-factory/payments-live-3m/run -H 'Content-Type: application/json'
curl -X POST http://localhost:8000/api/data-factory/massive-fraud-orders-3m/run -H 'Content-Type: application/json'
./.venv/bin/python scripts/promote_data_lake_layers.py
```

### Retour a l'etat initial

```bash
curl -X POST http://localhost:8000/api/system/reset-data \
  -H 'Content-Type: application/json' \
  --data-binary '{"confirm":true,"clear_runtime_artifacts":true,"stop_live_jobs":true}'
```

### Generer le pack de livraison

```bash
bash scripts/build_delivery_pack.sh
```

## Dashboards

- Overview: `http://localhost:7600/index.html`
- Fraude: `http://localhost:7600/fraud_dashboard.html`
- Typologies: `http://localhost:7600/fraud_types_dashboard.html`
- Identite: `http://localhost:7600/id_cards_dashboard.html`
- Transferts: `http://localhost:7600/transfer_kpi_dashboard.html`
- Use cases: `http://localhost:7600/use_cases_dashboard.html`

## Indicateurs importants

- `fraud_rate` = `fraudulent_payments / successful_payments`
- `total_alerts` = volume d'alertes regles, distinct du volume de paiements
- `customer_alert_coverage` = part des clients couverts par au moins une alerte
- KPI transfert = latence, debit, volume traite, sante pipeline

## Endpoints utiles

- `GET /api/stats`: KPI fraude globaux
- `GET /api/payments/stats?window_hours=24`: KPI paiements recentes et `fraud_rate` live
- `GET /api/data-lake/status`: etat bronze -> silver -> gold publie dans MinIO
- `GET /api/data-factory`: catalogue des actions live et pipeline
- `POST /api/data-factory/payments-live-3m/run`: flux paiements temps reel
- `POST /api/data-factory/massive-fraud-orders-3m/run`: episode fraude commandes massif sur 3 minutes
- `POST /api/data-factory/data-lake-pipeline/run`: promotion MinIO bronze -> silver -> gold

## Documentation racine

- [PATATOR_GUIDE.md](./PATATOR_GUIDE.md): demarrage automatise
- [INSTALLATION.md](./INSTALLATION.md): installation detaillee
- [QUICKSTART.md](./QUICKSTART.md): sequence courte de lancement
- [DEMO_PROJET.md](./DEMO_PROJET.md): runbook de demonstration
- [SUJET1_CHECKLIST.md](./SUJET1_CHECKLIST.md): checklist de validation
- [SOMMAIRE_MEMOIRE_TECHNIQUE.md](./SOMMAIRE_MEMOIRE_TECHNIQUE.md): plan conseille pour le memoire technique
- [PROMPT_PRESENTATION_IA.md](./PROMPT_PRESENTATION_IA.md): prompt a fournir a une IA pour generer la presentation
- [AUDIT_CONSIGNE_INITIALE.md](./AUDIT_CONSIGNE_INITIALE.md): cadrage initial et regles metier
- [AUDIT_RENDU_PROJET.md](./AUDIT_RENDU_PROJET.md): audit de conformite et hygiene de depot
- [AUDIT_FONCTIONNEL_FINAL.md](./AUDIT_FONCTIONNEL_FINAL.md): verification finale des features annoncees et de leur etat reel
- [PACK_RENDU.md](./PACK_RENDU.md): contenu et generation du pack de livraison

## Services exposes

- API FastAPI: `http://localhost:8000`
- Dashboard web: `http://localhost:7600`
- Kafka UI: `http://localhost:8082`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- MinIO console: `http://localhost:9001`

## Resultat attendu avant presentation

- `bash scripts/checklist_and_launch.sh` retourne `33/33 OK`
- `scripts/validate_sujet1.py` retourne `PASS 11/11`
- `scripts/validate_perfect_compliance.py` retourne `PASS 6/6`
- `scripts/data_quality_checks.py` retourne `18/18 PASS`
