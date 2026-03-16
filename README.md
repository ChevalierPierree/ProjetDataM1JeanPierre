# 🛒 KiVendTout - Architecture Data Engineering & IA

**Projet de Master 1 - Data Engineering & IA**  
**EFREI - Février 2026**

---

## 📋 À propos

Architecture de données complète pour plateforme e-commerce avec :
- 🛡️ Détection de fraude en temps réel
- 📊 Business Intelligence temps réel
- 🤖 Reconnaissance de cartes d'identité (IA)
- 🔄 Pipelines de données distribués
- 📈 Haute disponibilité et scalabilité

---

## 🚀 Démarrage rapide

### ⚡ Méthode PATATOR (Recommandée)

**Un seul mot lance tout !**

```bash
# Cloner le projet
git clone https://github.com/ChevalierPierree/ProjetDataM1JeanPierre.git
cd ProjetDataM1JeanPierre

# Environnement Python local (recommandé)
python3 -m venv .venv
source .venv/bin/activate

# Installer les dépendances nécessaires à PATATOR
python -m pip install --upgrade pip
python -m pip install -r requirements.patator.txt

# Lancer TOUT en une commande
chmod +x patator
./patator
```

🎯 **PATATOR** lance automatiquement :
- ✅ 13 services Docker (Kafka, Flink, PostgreSQL, MongoDB, etc.)
- ✅ Chargement des données (71,694 événements)
- ✅ Détection de fraude temps réel et ingestion des alertes
- ✅ API Backend (FastAPI sur port 8000)
- ✅ Dashboard Web (sur port 7600)
- ✅ Ouvre le dashboard dans le navigateur

**Durée** : 3-5 minutes | **Documentation** : [PATATOR_GUIDE.md](./PATATOR_GUIDE.md)

### 📐 KPI Fraude (définition)

- `fraud_rate` = `paiements frauduleux labelisés / paiements totaux` (en %)
- `total_alerts` = nombre d'alertes règles (peut être supérieur aux paiements frauduleux)
- `fraudulent_payments` = volume de paiements labelisés fraude
- `customer_alert_coverage` = `% de clients ayant au moins une alerte`

Ces définitions évitent un taux > 100% et rendent les chiffres dashboard cohérents.

### ✅ Conformité parfaite (RBAC, Data Lake sécurité, micro-batch, résilience, KPI transfert)

```bash
# 1) RBAC + quotas API
./.venv/bin/python scripts/test_api_rbac_rate_limit.py

# 2) Sécurité Data Lake (TLS + rotation secrets)
bash scripts/generate_minio_tls_certs.sh
bash scripts/rotate_minio_credentials.sh all

# 3) Flux micro-batch MongoDB -> PostgreSQL
./.venv/bin/python scripts/micro_batch_events_to_postgres.py --run-once --window-seconds 30

# 4) Tests de charge DB + résilience
./.venv/bin/python scripts/test_db_load.py --pg-requests 120 --mongo-requests 120 --concurrency 12
./.venv/bin/python scripts/test_resilience_failover.py --service postgres --dry-run

# 5) Validation globale
./.venv/bin/python scripts/validate_perfect_compliance.py
```

Preuves:
- `logs/api_rbac_rate_limit_report.json`
- `logs/db_load_test_report.json`
- `logs/resilience_failover_report.json`
- `logs/perfect_compliance_report.json`
- `logs/transfer_kpi_history.jsonl`

Nouveaux endpoints:
- `GET /api/micro-batch/stats`
- `GET /api/transfer/kpis`
- `GET /api/kpis/readable` (lecture humaine des KPI + interprétation)

Nouveau dashboard:
- `http://localhost:7600/transfer_kpi_dashboard.html`

---

### 🛠️ Méthode manuelle (pour développeurs)

```bash
# Créer le fichier .env
cp .env.example .env

# Démarrer les services Docker
docker compose up -d

# Charger les données
python3 scripts/load_data_to_postgres.py
python3 scripts/load_events_to_mongodb.py

# Configurer Kafka
python3 scripts/create_kafka_topics.py
python3 scripts/stream_events_to_kafka.py

# Lancer la détection de fraude
python3 scripts/fraud_detection_realtime.py

# Lancer l'API et le dashboard
python3 api/fraud_dashboard_api.py &
cd dashboard && python3 -m http.server 7600 &

# Accéder au dashboard
open http://localhost:7600/fraud_dashboard.html
```

---

## 📚 Documentation

Toute la documentation se trouve dans le dossier [`markdowns/`](./markdowns/) :

| Document | Description |
|----------|-------------|
| [**⚡ PATATOR Guide**](./PATATOR_GUIDE.md) | Script de démarrage automatique (NOUVEAU !) |
| [**🚀 Quick Start**](./QUICKSTART.md) | Démarrage en 3 commandes |
| [**🛠️ Installation**](./INSTALLATION.md) | Guide d'installation détaillé |
| [**🎤 Demo Soutenance**](./DEMO_SOUTENANCE.md) | Script de démo 5-7 minutes |
| [**� Récap Complet**](./RECAP_COMPLET_PROJET.md) | Vue d'ensemble du projet |
| [**�📖 README Complet**](./markdowns/README.md) | Documentation technique détaillée |
| [**🛠️ Stack Technique**](./markdowns/STACK_TECHNIQUE.md) | Justification des choix technologiques |
| [**📊 Récap Avancement**](./markdowns/RECAP_AVANCEMENT.md) | État d'avancement du projet |
| [**✅ Session Finale**](./markdowns/SESSION_FINALE.md) | Résumé de la session de setup |

---

## 🏗️ Architecture

```
PostgreSQL (OLTP) ─┐
MongoDB (NoSQL)    ├─→ Kafka (Streaming) ─→ Flink (Processing)
MinIO (Data Lake)  ─┘                              │
                                                   ↓
                                            PostgreSQL DWH
                                                   │
                                    ┌──────────────┼──────────────┐
                                    ↓              ↓              ↓
                                FastAPI        Superset      Grafana
                                 (API)           (BI)      (Monitoring)
```

---

## 🛠️ Stack Technologique

- **Base de données** : PostgreSQL, MongoDB
- **Data Lake** : MinIO (S3-compatible) + Parquet
- **Streaming** : Apache Kafka (cluster HA)
- **Processing** : Apache Flink
- **Orchestration** : Apache Airflow
- **Transformation** : dbt
- **IA/ML** : TensorFlow, OpenCV
- **API** : FastAPI
- **BI** : Apache Superset
- **Monitoring** : Prometheus + Grafana
- **Infra** : Docker Compose

---

## 🌐 Services & Accès

| Service | URL | Identifiants |
|---------|-----|--------------|
| MinIO Console | http://localhost:9001 | `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` (dans `.env`) |
| Kafka UI | http://localhost:8082 | - |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | - |
| PostgreSQL | localhost:5432 | postgres / postgres |
| MongoDB | localhost:27017 | admin / admin |

---

## 👥 Équipe

- **Pierre Chevalier** - Data Engineering & Infrastructure
- **[Votre binôme]** - [Rôle]

---

## 📝 Licence

Projet académique - EFREI M1 Data Engineering & IA - 2026

---

## 🆘 Support

Pour toute question, consultez la [documentation complète](./markdowns/README.md) ou créez une issue.

**Dernière mise à jour** : 25 février 2026
