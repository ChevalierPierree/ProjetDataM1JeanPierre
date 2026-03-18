# Runbook Demo Projet

## 1. Preparation

```bash
cd /Users/jeanmacario/Documents/GitHub/ProjetDataM1JeanPierre
source .venv/bin/activate
bash scripts/checklist_and_launch.sh
```

Controle rapide:

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/stats | jq '{total_alerts,fraud_rate,fraudulent_payments,total_payments,customer_alert_coverage}'
curl -s 'http://localhost:8000/api/payments/stats?window_hours=24' | jq '{total_payments,fraudulent_payments,fraud_rate,payment_methods}'
```

## 2. Sequence de demonstration

### Etape A - Vue globale

Ouvrir:
- `http://localhost:7600/index.html`
- `http://localhost:7600/fraud_dashboard.html`
- `http://localhost:7600/transfer_kpi_dashboard.html`

A montrer:
- indicateurs clefs,
- cadence live 1 seconde,
- etat des flux,
- bouton de reset data.

### Etape B - Cas metier

```bash
bash scripts/test_use_cases.sh
```

Cas a commenter:
- mineur + produit `Adult` -> bloque,
- majeur + produit `Adult` -> accepte,
- verification d'identite -> tracee,
- alerte HIGH -> visible dans le backlog.

### Etape C - Pipeline transfert

```bash
bash scripts/run_micro_batch.sh once
./.venv/bin/python scripts/promote_data_lake_layers.py
```

A commenter:
- fenetre traitee,
- nombre d'evenements,
- latence de traitement,
- debit du micro-batch.
- couches `silver` et `gold` publiees dans MinIO.

### Etape D - Flux paiements realiste

```bash
curl -X POST http://localhost:8000/api/data-factory/payments-live-3m/run \
  -H 'Content-Type: application/json'
```

A commenter:
- le flux injecte des checkouts acceptes avec paiements reussis,
- une partie est marquee frauduleuse selon le profil de risque,
- `GET /api/payments/stats?window_hours=24` varie pendant le flux,
- `GET /api/stats` varie aussi, mais plus lentement car il porte sur tout l'historique.

### Etape E - Episode fraude commandes

```bash
curl -X POST http://localhost:8000/api/data-factory/massive-fraud-orders-3m/run \
  -H 'Content-Type: application/json'
```

A commenter:
- le flux pousse en meme temps des commandes a risque et des alertes HIGH,
- les tentatives mineures 18+ montent dans la vue identite,
- les paiements frauduleux montent dans la vue fraude/paiements,
- la pression d'alertes devient visible sur `Fraude` et `Typologies`.

### Etape F - Notifications

```bash
bash scripts/test_alert_notifications.sh
```

Etat actuel:
- le circuit est fonctionnel,
- le mode par defaut est `preview`, donc un apercu de mail est genere localement.

### Etape G - Retour a l'etat initial

Depuis un dashboard, cliquer `Reset data`.

Equivalent API:

```bash
curl -X POST http://localhost:8000/api/system/reset-data \
  -H 'Content-Type: application/json' \
  --data-binary '{"confirm":true,"clear_runtime_artifacts":true,"stop_live_jobs":true}'
```

## 3. Messages clefs

- Les dashboards sont alimentes en streaming SSE avec refresh 1 seconde.
- Les controles de majorite sont journalises et visibles dans les vues fraude et identite.
- Le `fraud_rate` global repose sur les paiements reussis; le flux `payments-live-3m` sert a le faire varier de maniere metier.
- Le Data Lake MinIO est exploitable en `bronze -> silver -> gold` via `scripts/promote_data_lake_layers.py`.
- Le reset permet de revenir a un socle de donnees stable avant une nouvelle demonstration.
- Les preuves techniques sont disponibles dans `logs/` et dans le pack de livraison.

## 4. Plan de repli

```bash
pkill -f 'api/fraud_dashboard_api.py' || true
source .venv/bin/activate
python api/fraud_dashboard_api.py
bash scripts/checklist_and_launch.sh
```
