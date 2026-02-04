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

# Installer les dépendances
pip3 install -r requirements.txt

# Lancer TOUT en une commande
chmod +x patator
./patator
```

🎯 **PATATOR** lance automatiquement :
- ✅ 13 services Docker (Kafka, Flink, PostgreSQL, MongoDB, etc.)
- ✅ Chargement des données (71,694 événements)
- ✅ Détection de fraude (10,857 alertes générées)
- ✅ API Backend (FastAPI sur port 8000)
- ✅ Dashboard Web (sur port 7600)
- ✅ Ouvre le dashboard dans le navigateur

**Durée** : 3-5 minutes | **Documentation** : [PATATOR_GUIDE.md](./PATATOR_GUIDE.md)

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
| MinIO Console | http://localhost:9001 | minio / minio123 |
| Kafka UI | http://localhost:8080 | - |
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

**Dernière mise à jour** : 3 février 2026
