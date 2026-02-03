# 🛒 KiVendTout - Architecture Data Engineering & IA

**Projet de Master 1 - Data Engineering & IA**  
**Sujet** : Architecture de données pour plateforme e-commerce (détection fraude, BI temps réel, reconnaissance CNI)  
**Bloc** : RNCP40875 - Bloc 1 - Concevoir, développer et déployer une architecture de données  
**Date** : Février 2026

---

## 📋 Table des matières

- [Contexte du projet](#-contexte-du-projet)
- [Architecture technique](#-architecture-technique)
- [Stack technologique](#-stack-technologique)
- [Prérequis](#-prérequis)
- [Installation](#-installation)
- [Démarrage rapide](#-démarrage-rapide)
- [Services & Accès](#-services--accès)
- [Structure du projet](#-structure-du-projet)
- [Workflows](#-workflows)
- [Documentation](#-documentation)

---

## 🎯 Contexte du projet

### Problématiques métier
KiVendTout, plateforme e-commerce en forte croissance, fait face à :
- ✅ Augmentation des **fraudes aux paiements**
- ✅ Difficulté à **analyser le comportement utilisateurs**
- ✅ **Temps de réponse longs** pour les équipes métiers
- ✅ Incapacité à **historiser les événements** utilisateurs
- ✅ Nouvelle **contrainte légale** : contrôle d'identité pour ventes réglementées

### Objectifs du projet
1. Stocker les données critiques avec **intégrité totale** (OLTP)
2. Exploiter les **événements utilisateurs** en temps réel
3. Centraliser les données dans un **Data Lake** scalable
4. Détecter les **fraudes en temps réel** via stream processing
5. Exposer les données via **API standardisée**
6. Réduire les **temps d'analyse BI**
7. Garantir **scalabilité** et **haute disponibilité**
8. Assurer **conformité RGPD** et sécurité
9. Améliorer la **qualité des données**
10. Déployer un modèle **IA de reconnaissance de CNI**

---

## 🏗️ Architecture technique

```
┌─────────────────────────────────────────────────────────────────┐
│                        SOURCES DE DONNÉES                        │
│     Web    │   Mobile   │   CRM   │  Paiement  │  Logistique   │
└──────┬─────────┬──────────┬──────────┬────────────┬─────────────┘
       │         │          │          │            │
       └─────────┴──────────┴──────────┴────────────┘
                             │
                      ┌──────▼──────┐
                      │   KAFKA     │ Streaming (3 brokers HA)
                      └──────┬──────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────▼─────┐  ┌─────▼─────┐  ┌────▼────┐
        │   FLINK   │  │  MongoDB  │  │  MinIO  │
        │(Détection │  │  (Logs)   │  │(D. Lake)│
        │  fraude)  │  └───────────┘  └────┬────┘
        └─────┬─────┘                      │
              │                            │
        ┌─────▼────────────────────────────▼─────┐
        │         PostgreSQL (OLTP)              │
        │   Clients │ Commandes │ Paiements      │
        └─────┬────────────────────────────────────┘
              │
        ┌─────▼─────┐
        │  AIRFLOW  │ Orchestration ETL/ELT
        └─────┬─────┘
              │
        ┌─────▼─────┐
        │    dbt    │ Transformations SQL + Tests
        └─────┬─────┘
              │
     ┌────────┼────────┐
     │        │        │
┌────▼───┐ ┌──▼────┐ ┌▼─────────┐
│SUPERSET│ │FastAPI│ │TensorFlow│
│  (BI)  │ │ (API) │ │   (IA)   │
└────────┘ └───────┘ └──────────┘
     │        │        │
     └────────┴────────┘
              │
     ┌────────▼────────┐
     │  PROMETHEUS +   │
     │    GRAFANA      │
     │  (Monitoring)   │
     └─────────────────┘
```

---

## 🛠️ Stack technologique

| Composant | Technologie | Version | Rôle |
|-----------|-------------|---------|------|
| **OLTP** | PostgreSQL | 15+ | Base relationnelle ACID |
| **NoSQL** | MongoDB | 7+ | Logs & événements |
| **Data Lake** | MinIO + Parquet | Latest | Stockage massif S3-compatible |
| **Streaming** | Apache Kafka | 3.6+ | Message broker haute volumétrie |
| **Processing** | Apache Flink | 1.18+ | Traitement temps réel |
| **Orchestration** | Apache Airflow | 2.8+ | Workflow ETL/ELT |
| **Transformation** | dbt | 1.7+ | SQL transformations |
| **IA/ML** | TensorFlow + OpenCV | 2.15+ | Reconnaissance CNI |
| **API** | FastAPI | 0.109+ | REST API + Swagger |
| **BI** | Apache Superset | 3.0+ | Dashboards interactifs |
| **Monitoring** | Prometheus + Grafana | Latest | Métriques & alerting |
| **Quality** | Great Expectations | 0.18+ | Data validation |
| **Infra** | Docker Compose | Latest | Containerisation |

**Langage principal** : Python 3.10+  
**Coût total** : 0€ (100% open source)

---

## ✅ Prérequis

### Logiciels requis
- ✅ **Docker Desktop** (installé) - [Télécharger](https://www.docker.com/products/docker-desktop)
- ✅ **Git** (installé sur macOS par défaut)
- ✅ **Python 3.10+** - Installation : `brew install python@3.10`
- ⚠️ **16 GB RAM minimum** (32 GB recommandé)
- ⚠️ **50 GB d'espace disque**

### Vérification
```bash
docker --version          # Docker version 24.0+
docker compose version    # Docker Compose version v2.20+
python3 --version         # Python 3.10+
git --version            # git version 2.30+
```

---

## 📦 Installation

### 1. Cloner le repository
```bash
git clone <votre-repo-git>
cd Patator
```

### 2. Créer l'environnement Python
```bash
# Créer un environnement virtuel
python3 -m venv venv

# Activer l'environnement
source venv/bin/activate  # macOS/Linux

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configuration des variables d'environnement
```bash
# Copier le template
cp .env.example .env

# Éditer avec vos valeurs
nano .env  # ou vim, code, etc.
```

---

## 🚀 Démarrage rapide

### Démarrer tous les services
```bash
# Démarrer l'infrastructure complète
docker compose up -d

# Vérifier que tous les services sont UP
docker compose ps

# Voir les logs en temps réel
docker compose logs -f
```

### Démarrer services individuellement
```bash
# Seulement la base de données
docker compose up -d postgres

# Seulement Kafka + Zookeeper
docker compose up -d zookeeper kafka-1 kafka-2 kafka-3

# Seulement le monitoring
docker compose up -d prometheus grafana
```

### Arrêter les services
```bash
# Arrêter tout
docker compose down

# Arrêter + supprimer les volumes (⚠️ perte de données)
docker compose down -v
```

---

## 🌐 Services & Accès

Une fois les services démarrés :

| Service | URL | Identifiants | Description |
|---------|-----|--------------|-------------|
| **PostgreSQL** | `localhost:5432` | `postgres` / `postgres` | Base de données relationnelle |
| **MongoDB** | `localhost:27017` | `admin` / `admin` | Base NoSQL |
| **MinIO** | http://localhost:9001 | `minio` / `minio123` | Interface Data Lake |
| **Kafka UI** | http://localhost:8080 | - | Monitoring Kafka |
| **Airflow** | http://localhost:8081 | `airflow` / `airflow` | Orchestration |
| **Superset** | http://localhost:8088 | `admin` / `admin` | Business Intelligence |
| **FastAPI** | http://localhost:8000/docs | - | API Documentation (Swagger) |
| **Grafana** | http://localhost:3000 | `admin` / `admin` | Dashboards monitoring |
| **Prometheus** | http://localhost:9090 | - | Métriques |

---

## 📁 Structure du projet

```
Patator/
├── README.md                      # Ce fichier
├── STACK_TECHNIQUE.md            # Documentation stack
├── docker-compose.yml            # Orchestration services
├── .env.example                  # Template variables d'environnement
├── .gitignore                    # Fichiers à ignorer
├── requirements.txt              # Dépendances Python
│
├── airflow/                      # Apache Airflow
│   ├── dags/                     # Workflows ETL/ELT
│   │   ├── etl_postgres_to_lake.py
│   │   ├── etl_lake_to_warehouse.py
│   │   └── data_quality_checks.py
│   ├── plugins/                  # Plugins custom
│   └── config/                   # Configuration
│
├── api/                          # FastAPI
│   ├── main.py                   # Point d'entrée API
│   ├── routers/                  # Routes REST
│   │   ├── customers.py
│   │   ├── orders.py
│   │   ├── fraud.py
│   │   └── identity.py
│   ├── models/                   # Modèles Pydantic
│   ├── schemas/                  # Schémas SQL
│   └── Dockerfile
│
├── dbt/                          # dbt transformations
│   ├── models/                   # Modèles SQL
│   │   ├── staging/              # Tables staging
│   │   ├── intermediate/         # Tables intermédiaires
│   │   └── mart/                 # Tables finales (DWH)
│   ├── tests/                    # Tests data quality
│   ├── macros/                   # Macros réutilisables
│   └── dbt_project.yml
│
├── flink/                        # Apache Flink
│   ├── jobs/                     # Jobs stream processing
│   │   ├── fraud_detection.py
│   │   └── real_time_aggregations.py
│   └── config/
│
├── ml/                           # Machine Learning
│   ├── notebooks/                # Jupyter notebooks
│   │   ├── 01_eda.ipynb
│   │   ├── 02_fraud_model.ipynb
│   │   └── 03_cni_recognition.ipynb
│   ├── models/                   # Modèles entraînés
│   ├── data/                     # Datasets
│   └── scripts/
│       ├── train_cni_model.py
│       └── inference_cni.py
│
├── data/                         # Données locales
│   ├── raw/                      # Données brutes
│   ├── processed/                # Données traitées
│   └── external/                 # Données externes
│
├── database/                     # Scripts SQL
│   ├── postgres/
│   │   ├── init/
│   │   │   └── 01_create_schema.sql
│   │   └── migrations/
│   └── mongodb/
│       └── init/
│
├── kafka/                        # Kafka configuration
│   ├── producers/                # Producteurs de messages
│   │   ├── web_events.py
│   │   └── payment_events.py
│   └── consumers/                # Consommateurs
│
├── monitoring/                   # Monitoring & observabilité
│   ├── prometheus/
│   │   └── prometheus.yml
│   ├── grafana/
│   │   ├── dashboards/
│   │   └── datasources/
│   └── alerting/
│
├── tests/                        # Tests
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── docs/                         # Documentation
│   ├── architecture/
│   ├── api/
│   └── runbook/
│
└── scripts/                      # Scripts utilitaires
    ├── setup.sh
    ├── generate_sample_data.py
    └── run_tests.sh
```

---

## 🔄 Workflows

### 1. Pipeline Batch (Quotidien)
```
PostgreSQL → Airflow → MinIO (Parquet) → dbt → PostgreSQL (DWH) → Superset
```

### 2. Pipeline Streaming (Temps réel)
```
Sources → Kafka → Flink → PostgreSQL/MongoDB → FastAPI → Alertes
```

### 3. Pipeline IA
```
Upload CNI → FastAPI → TensorFlow/OpenCV → Validation → PostgreSQL
```

---

## 📚 Documentation

### Guides de démarrage
- [Guide PostgreSQL](docs/database/postgresql.md)
- [Guide Kafka](docs/streaming/kafka.md)
- [Guide Airflow](docs/orchestration/airflow.md)
- [Guide API](docs/api/fastapi.md)
- [Guide ML](docs/ml/model_training.md)

### Ressources externes
- [Documentation PostgreSQL](https://www.postgresql.org/docs/)
- [Documentation Kafka](https://kafka.apache.org/documentation/)
- [Documentation Airflow](https://airflow.apache.org/docs/)
- [Documentation FastAPI](https://fastapi.tiangolo.com/)

---

## 👥 Équipe

- **Étudiant 1** : [Nom] - [Rôle principal]
- **Étudiant 2** : [Nom] - [Rôle principal]

---

## 📝 Licence

Projet académique - EFREI M1 Data Engineering & IA - 2026

---

## 🆘 Support

Pour toute question :
1. Consulter la [documentation](docs/)
2. Vérifier les [issues GitHub](../../issues)
3. Contacter l'équipe

---

**Dernière mise à jour** : 3 février 2026  
**Statut du projet** : 🚧 En développement
