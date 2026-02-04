# Fraud MVP - KiVendTout

**Objectif** : detecter des paiements suspects en temps reel via des regles simples.

## Flux cible

`payments.csv` -> Kafka `payments` -> Fraud Detector ->
- PostgreSQL `fraud_alerts`
- Kafka `fraud-alerts`

## Prerequis

- Docker Compose demarre
- Kafka + PostgreSQL accessibles
- Dependencies Python (fraude uniquement)

```bash
python3 -m pip install -r requirements-fraud.txt
```

## Etapes

1. Creer les topics Kafka

```bash
./scripts/streaming/create_topics.sh
```

2. Produire les paiements

```bash
python3 scripts/fraud/producer_payments.py \
  --file kivendtout_dataset/payments.csv \
  --max-per-second 200
```

3. Lancer le detecteur de fraude

```bash
python3 scripts/fraud/fraud_detector.py \
  --from-beginning
```

## Regles implementees

- `high_amount` : montant > 100 et premier achat
- `country_mismatch` : pays paiement != pays client
- `velocity` : > 5 tentatives en 10 minutes
- `device_change` : changement device + IP en < 1h
- `time_anomaly` : achat entre 03h et 06h

## Validation

- `fraud_alerts` alimentee dans PostgreSQL
- Topic `fraud-alerts` avec messages emis

## Commandes utiles

Compter les alertes en base

```bash
docker exec -it kivendtout-postgres psql -U postgres -d kivendtout -c "SELECT COUNT(*) FROM fraud_alerts;"
```

Afficher un exemple

```bash
docker exec -it kivendtout-postgres psql -U postgres -d kivendtout -c "SELECT * FROM fraud_alerts ORDER BY alert_date DESC LIMIT 5;"
```
