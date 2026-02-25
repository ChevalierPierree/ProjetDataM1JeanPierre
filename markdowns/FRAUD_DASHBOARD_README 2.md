# 🛡️ KiVendTout - Dashboard Détection de Fraude

## 🚀 Démarrage Rapide

### 1. Démarrer l'infrastructure
```bash
cd /Users/pierrechevalier/Desktop/PERSO/EFREI/M1\ DATA/Patator
docker compose up -d
```

### 2. Streamer les événements vers Kafka
```bash
python3 scripts/stream_events_to_kafka.py
# ✅ 71,694 événements streamés
```

### 3. Lancer la détection de fraude
```bash
python3 scripts/fraud_detection_realtime.py
# ✅ 11 règles actives (6 basiques + 5 avancées)
# ✅ ~5,500 alertes détectées
```

### 4. Démarrer l'API Dashboard
```bash
python3 api/fraud_dashboard_api.py
# ✅ API sur http://localhost:8000
```

### 5. Ouvrir le Dashboard Web
```bash
# Terminal 1 : Serveur HTTP
cd dashboard && python3 -m http.server 7500

# Navigateur : http://localhost:7500/fraud_dashboard.html
```

---

## 📊 Endpoints API

### Health Check
```bash
curl http://localhost:8000/health
```

### Récupérer les Statistiques
```bash
curl http://localhost:8000/api/stats | jq .
```

### Liste des Alertes
```bash
# Toutes les alertes
curl http://localhost:8000/api/alerts | jq .

# Filtrer par sévérité HIGH
curl "http://localhost:8000/api/alerts?severity=HIGH" | jq .

# Filtrer par statut PENDING_REVIEW
curl "http://localhost:8000/api/alerts?status=PENDING_REVIEW&limit=10" | jq .
```

### Prendre une Décision sur une Alerte
```bash
# APPROVE
curl -X POST http://localhost:8000/api/alerts/{ALERT_ID}/decide \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "APPROVE",
    "decided_by": "analyst@kivendtout.com",
    "notes": "Faux positif - Client régulier"
  }'

# BLOCK
curl -X POST http://localhost:8000/api/alerts/{ALERT_ID}/decide \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "BLOCK",
    "decided_by": "analyst@kivendtout.com",
    "notes": "Fraude confirmée - Blocage compte"
  }'

# INVESTIGATE
curl -X POST http://localhost:8000/api/alerts/{ALERT_ID}/decide \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "INVESTIGATE",
    "decided_by": "analyst@kivendtout.com",
    "notes": "Nécessite vérification manuelle"
  }'
```

### Synchroniser depuis Kafka
```bash
curl -X POST http://localhost:8000/api/sync
# ✅ Importe les alertes du topic fraud-alerts vers PostgreSQL
```

---

## 🔍 Règles de Détection

### Règles Basiques (6)
1. **FIRST_PAYMENT** - Premier paiement client (40 pts)
2. **NEW_CUSTOMER** - Client < 7 jours (30 pts)
3. **UNUSUAL_HOUR** - Paiement 2h-6h (35 pts)
4. **MOBILE_DEVICE** - Appareil mobile (20 pts)
5. **DIRECT_TRAFFIC** - Sans référent (15 pts)
6. **PAYMENT_FAILED** - Échec paiement (50 pts)

### Règles Avancées (5) 🆕
7. **VELOCITY_HIGH** - 3+ paiements en 10 minutes (45 pts)
8. **NEW_DEVICE** - Nouveau device fingerprint (30 pts)
9. **UNUSUAL_AMOUNT** - Montant > 3x moyenne client (40 pts)
10. **FAST_CHECKOUT** - Checkout < 30 secondes (35 pts)
11. **GEO_MISMATCH** - Pays différent du profil (25 pts)

**Seuil de fraude** : ≥ 60 points

**Sévérité** :
- 🔴 **HIGH** : ≥ 85 points
- 🟠 **MEDIUM** : 60-84 points
- 🔵 **LOW** : < 60 points

---

## 🗂️ Structure Base de Données

### Table `fraud_alerts` (PostgreSQL)
```sql
alert_id VARCHAR(100) PRIMARY KEY
alert_timestamp TIMESTAMP
event_timestamp TIMESTAMP
customer_id VARCHAR(20)
session_id VARCHAR(50)
event_type VARCHAR(50)
device VARCHAR(50)
utm_source VARCHAR(50)
customer_country VARCHAR(10)
previous_payments INT
is_new_customer BOOLEAN
fraud_reasons TEXT
risk_score INT
status VARCHAR(20) DEFAULT 'PENDING_REVIEW'
severity VARCHAR(10)
decision VARCHAR(20)
decided_at TIMESTAMP
decided_by VARCHAR(100)
notes TEXT
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

---

## 🎛️ Dashboard Web - Features

### Stats Dashboard
- Total alertes
- Taux de fraude (%)
- Alertes HIGH severity
- En attente de review

### Filtres
- **Status** : PENDING_REVIEW, INVESTIGATING, APPROVED, BLOCKED
- **Severity** : HIGH, MEDIUM, LOW

### Actions Analyst
- ✅ **APPROVE** - Transaction légitime (bouton vert)
- 🚫 **BLOCK** - Fraude confirmée (bouton rouge)
- 🔍 **INVESTIGATE** - Investigation nécessaire (bouton orange)

### Features Automatiques
- 🔄 Auto-refresh toutes les 30 secondes
- 📊 Stats mises à jour en temps réel
- 🔄 Bouton "Sync from Kafka" pour import manuel
- 📄 Pagination (15 alertes/page)

---

## 🐳 Services Docker

```bash
# Vérifier les services
docker compose ps

# Services actifs :
✅ PostgreSQL 15       localhost:5432
✅ MongoDB 7           localhost:27017
✅ Kafka Cluster       9092, 9093, 9094
✅ Flink JobManager    localhost:8083
✅ Grafana             localhost:4000
✅ Prometheus          localhost:9090
✅ Kafka UI            localhost:8082
```

---

## 🔧 Troubleshooting

### Erreur : "column does not exist"
```bash
# Recréer la table fraud_alerts
docker compose exec -T postgres psql -U postgres -d kivendtout \
  -f /docker-entrypoint-initdb.d/02_fraud_alerts.sql
```

### Erreur : "NoBrokersAvailable"
```bash
# Redémarrer tous les brokers Kafka
docker compose restart kafka-1 kafka-2 kafka-3
sleep 10  # Attendre la stabilisation
```

### Erreur : "Port already in use"
```bash
# Trouver le processus utilisant le port
lsof -i :8000  # Remplacer 8000 par le port concerné
kill -9 <PID>  # Tuer le processus
```

### Topic Kafka vide
```bash
# Re-streamer les événements
python3 scripts/stream_events_to_kafka.py
```

### Logs de l'API
```bash
tail -f logs/fraud_dashboard_api.log
```

### Logs de détection
```bash
tail -f logs/fraud_detection_advanced.log
```

---

## 📈 Métriques de Performance

### Détection en Temps Réel
- ⚡ **~169 événements/seconde**
- 📊 **6,461 événements traités**
- 🚨 **5,526 fraudes détectées** (85.53%)
- ⏱️ **38 secondes** pour traiter 7,563 paiements

### Infrastructure
- 🐳 **13 containers Docker**
- 📦 **3 brokers Kafka** (high availability)
- 🧠 **Flink** : 4 task slots, parallelism 2
- 💾 **PostgreSQL** : 8 tables, 4,305 alertes

---

## 📝 Logs & Monitoring

### Kafka UI
```
http://localhost:8082
```
- Topics : user-events, payments, fraud-alerts
- Offsets, consumer groups, messages

### Flink Web UI
```
http://localhost:8083
```
- Jobs, task managers, checkpoints

### Grafana Dashboards
```
http://localhost:4000
```
- Métriques Kafka, PostgreSQL, système

### Prometheus Metrics
```
http://localhost:9090
```
- Time-series metrics, alerting rules

---

## 🎓 Documentation Complète

Pour un rapport détaillé, voir :
```
PILIER3_COMPLETION_REPORT.md
```

---

**Auteur** : Pierre Chevalier  
**Projet** : M1 Data Engineering - EFREI  
**Date** : Février 2026
