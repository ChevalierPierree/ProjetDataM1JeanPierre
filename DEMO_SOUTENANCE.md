# Checklist Demo Soutenance (5-7 min)

## 1. Préparation (avant passage)

```bash
cd /Users/jeanmacario/Documents/GitHub/ProjetDataM1JeanPierre
source .venv/bin/activate
docker compose ps
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/stats | jq '{total_alerts,fraud_rate,fraudulent_payments,total_payments,customer_alert_coverage}'
```

Critère: `status=healthy` et KPI fraude cohérents (fraud_rate <= 100).

Si sécurité API activée (`API_KEY_REQUIRED=true`), ajouter:

```bash
export API_HEADER="X-API-Key"
export API_KEY="demo-admin-key"
curl -s -H "$API_HEADER: $API_KEY" http://localhost:8000/api/stats | jq .
```

## 2. Déroulé oral recommandé

### Etape A - Lancement orchestré (45s)

```bash
./patator
```

Message attendu: `PATATOR EST OPERATIONNEL`.

### Etape B - Vérification API (45s)

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/stats | jq .
```

Point à dire:
- `fraud_rate` = `fraudulent_payments / total_payments`
- `total_alerts` est un signal règles, pas un volume transactions.

Lecture simplifiée (sans calcul mental):

```bash
curl -s "http://localhost:8000/api/kpis/readable?limit=200&micro_batch_window_hours=24" | jq '.fraud.headline,.fraud.risk_level,.transfer.headline,.transfer.micro_batch_status,.fraud.interpretation,.transfer.interpretation'
```

### Etape C - Dashboard analyst (2-3 min)

Ouvrir:
- `http://localhost:7600/fraud_dashboard.html`
- `http://localhost:7600/transfer_kpi_dashboard.html`

A montrer:
- KPI globaux
- filtres statut/severite
- détail d'une alerte (raisons, risk score, device, pays)
- action analyste (`APPROVE`, `BLOCK`, `INVESTIGATE`).
- KPI transfert standardisés: latence/capacité/vitesse (dashboard transfert).

### Etape D - Observabilité (1-2 min)

Ouvrir:
- Kafka UI: `http://localhost:8082`
- Flink: `http://localhost:8083`
- Grafana: `http://localhost:3000`
- Prometheus: `http://localhost:9090`

## 3. Questions jury - réponses courtes

- Pourquoi le taux n'est plus >100%?
  - Parce qu'il est calculé sur les paiements, pas sur les alertes.
- Pourquoi autant d'alertes?
  - Plusieurs règles peuvent déclencher sur un même client/paiement.
- Comment industrialiser?
  - Versionner schéma, tests API, tests qualité data, CI/CD.

## 4. Plan de repli (si incident live)

```bash
pkill -f 'api/fraud_dashboard_api.py' || true
source .venv/bin/activate
python api/fraud_dashboard_api.py
```

Puis re-vérifier:

```bash
curl -s http://localhost:8000/health
```
