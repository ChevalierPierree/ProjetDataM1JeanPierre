# 🎯 ARCHITECTURE PROJET KIVENDTOUT - GRANDES CATÉGORIES STRATÉGIQUES

**Date** : 3 février 2026  
**Client** : KiVendTout (E-commerce)  
**Objectif** : Répondre aux 11 exigences de la direction

---

## 📊 STRUCTURE DU PROJET EN 6 PILIERS

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROJET KIVENDTOUT                            │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │ PILIER 1│          │ PILIER 2│          │ PILIER 3│
   │ Stockage│          │Streaming│          │  Fraude │
   │  Fiable │          │Temps Réel│         │ Temps Réel│
   └─────────┘          └─────────┘          └─────────┘
        │                     │                     │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │ PILIER 4│          │ PILIER 5│          │ PILIER 6│
   │Data Lake│          │Exposition│         │    IA   │
   │Analytics│          │   API   │          │Conformité│
   └─────────┘          └─────────┘          └─────────┘
```

---

## 🏛️ PILIER 1 : FONDATIONS - STOCKAGE FIABLE & GOUVERNANCE

### 🎯 Objectifs métier

- **Exigence #1** : Système fiable pour données critiques avec intégrité totale
- **Exigence #9** : Conformité sécurité et protection données
- **Exigence #10** : Améliorer qualité des données

### 🔧 Technologies

- **PostgreSQL 15** (OLTP transactionnel ACID)
- **dbt** (Data Build Tool - transformations + tests qualité)
- **Great Expectations** (validation données)

### 📋 Livrables

1. **Base PostgreSQL complète**
   - Schema normalisé (3NF)
   - Tables : customers, products, orders, order_items, payments, sessions, fraud_alerts
   - Contraintes : PRIMARY KEY, FOREIGN KEY, CHECK, UNIQUE
   - Indexes optimisés (B-tree, Hash)
   - Triggers pour audit trail
2. **Gouvernance des données**

   - Dictionnaire de données
   - Lineage (traçabilité origine → destination)
   - Politique RGPD (anonymisation, droit à l'oubli)
   - Chiffrement au repos (pgcrypto)
   - Backup automatique quotidien

3. **Qualité des données**
   - Tests dbt (unicité, non-null, valeurs acceptables)
   - Monitoring anomalies (Great Expectations)
   - Reconciliation entre sources
   - Documentation auto-générée

### ✅ Statut actuel : **85% FAIT**

- ✅ PostgreSQL opérationnel (8 tables, 16k lignes)
- ✅ Contraintes FK + indexes
- ⏳ dbt à installer (tests qualité)
- ⏳ Chiffrement + backup à configurer

---

## ⚡ PILIER 2 : STREAMING - CAPTURE ÉVÉNEMENTS TEMPS RÉEL

### 🎯 Objectifs métier

- **Exigence #2** : Exploiter tous les événements utilisateurs (clics, navigation, panier, paiements)
- **Exigence #7** : Garantir scalabilité face à croissance trafic

### 🔧 Technologies

- **Apache Kafka 3.6** (streaming distribué, 3 brokers HA)
- **MongoDB 7** (stockage flexible événements)
- **Kafka Connect** (connecteurs sources/sinks)
- **Schema Registry** (versioning schemas Avro)

### 📋 Livrables

1. **Pipeline ingestion événements**
   - Topics Kafka : `user-events`, `payments`, `orders`, `cart-events`
   - Producteurs Python (site web, app mobile)
   - Replication factor = 3 (haute dispo)
   - Partitioning par customer_id (parallélisme)
2. **Stockage NoSQL événements**

   - Collection MongoDB `events` (71k documents)
   - Indexes sur customer_id, session_id, event_type, timestamp
   - TTL automatique (rétention 2 ans)
   - Agrégations pré-calculées (sessions/jour, produits vus)

3. **Architecture hautement disponible**
   - Kafka cluster 3 brokers (tolérance panne 1 nœud)
   - Zookeeper ensemble (coordination)
   - Consumer groups (load balancing)
   - Monitoring Kafka UI + JMX metrics

### ✅ Statut actuel : **25% FAIT**

- ✅ Kafka 3 brokers installés
- ✅ MongoDB installé
- ✅ 71,694 events.jsonl prêts
- ❌ Topics pas créés
- ❌ Producers/Consumers pas codés
- ❌ Events pas dans MongoDB

### 🚀 Démarrage (MVP streaming)

**Objectif** : valider un flux simple et mesurable (JSONL -> Kafka -> MongoDB).

**Plan MVP** :
1. Créer les topics Kafka `user-events`, `payments`, `orders`, `cart-events` avec 3 partitions et un facteur de réplication 3.
2. Produire les événements depuis `kivendtout_dataset/events.jsonl` vers `user-events`.
3. Consommer `user-events` et insérer dans la collection MongoDB `events`.
4. Ajouter les index MongoDB et une rétention TTL de 2 ans.
5. Valider les volumes et la latence de bout en bout.

**Artefacts** :
1. `scripts/streaming/create_topics.sh`
2. `scripts/streaming/producer_events.py`
3. `scripts/streaming/consumer_events_to_mongo.py`
4. `markdowns/STREAMING_MVP.md` (mode opératoire + métriques)

---

## 🚨 PILIER 3 : SÉCURITÉ - DÉTECTION FRAUDE TEMPS RÉEL

### 🎯 Objectifs métier

- **Exigence #4** : Analyser événements en temps réel pour identifier fraudes
- **Contrainte** : Augmentation fraudes aux paiements

### 🔧 Technologies

- **Apache Flink 1.18** (stream processing CEP)
- **MLflow** (versioning modèles ML)
- **Scikit-learn / XGBoost** (modèles fraude)

### 📋 Livrables

1. **Règles de détection temps réel (Flink)**

   ```
   RÈGLE 1 - High Amount    : montant > 100€ ET premier achat
   RÈGLE 2 - Country Mismatch: pays paiement ≠ pays client
   RÈGLE 3 - Velocity        : >5 tentatives en 10 minutes
   RÈGLE 4 - Device Change   : changement device + IP en <1h
   RÈGLE 5 - Time Anomaly    : achat 3h-6h du matin (suspect)
   ```

2. **Pipeline Flink**

   - Source : Kafka topic `payments`
   - CEP Pattern Matching (séquences suspectes)
   - Enrichissement avec PostgreSQL (historique client)
   - Sink : Kafka topic `fraud-alerts` + PostgreSQL table
   - Windowing : sessions 30 min, tumbling 5 min

3. **Modèle ML supervisé**

   - Features : montant, heure, device, pays, historique
   - Algorithme : XGBoost (classification binaire)
   - Training : 1,583 paiements avec labels (19 fraudes)
   - Métriques : Precision/Recall/F1 (seuil optimal)
   - Déploiement : MLflow model serving

4. **Dashboards temps réel**
   - Alertes fraude (temps réel)
   - Taux de faux positifs/négatifs
   - Top règles déclenchées
   - Impact financier évité

### ✅ Statut actuel : **10% FAIT**

- ✅ 19 paiements frauduleux labellés en PostgreSQL
- ✅ Table fraud_alerts créée
- ❌ Flink pas configuré
- ❌ Règles pas implémentées
- ❌ Modèle ML pas entraîné

### 🚀 Démarrage (MVP fraude)

**Objectif** : simuler une détection temps réel avec règles simples et sorties traçables.

**Plan MVP** :
1. Producer Kafka `payments` depuis `kivendtout_dataset/payments.csv`
2. Consumer `fraud_detector.py` applique les règles
3. Écrit dans PostgreSQL `fraud_alerts`
4. Émet dans Kafka `fraud-alerts`

**Artefacts** :
1. `scripts/fraud/producer_payments.py`
2. `scripts/fraud/fraud_detector.py`
3. `markdowns/FRAUD_MVP.md`


---

## 🗄️ PILIER 4 : DATA LAKE & ANALYTICS - CENTRALISATION & BI

### 🎯 Objectifs métier

- **Exigence #3** : Centraliser données brutes (historisation complète)
- **Exigence #6** : Réduire temps d'analyse pour BI décisionnel

### 🔧 Technologies

- **MinIO** (S3-compatible Data Lake)
- **Apache Parquet** (format columnar optimisé)
- **Apache Superset 3.0** (BI open-source)
- **Apache Airflow 2.8** (orchestration ETL/ELT)
- **dbt** (transformations SQL)

### 📋 Livrables

1. **Architecture Data Lake (Medallion)**

   ```
   Bronze Layer (Raw)
   ├── /raw/postgres/*.parquet      (dump quotidien)
   ├── /raw/mongodb/*.parquet        (events)
   ├── /raw/kafka/*.parquet          (stream archives)
   └── /raw/id_cards/*.png           (images CNI)

   Silver Layer (Cleaned)
   ├── /curated/customers.parquet    (dédupliqués, validés)
   ├── /curated/orders.parquet       (enrichis)
   └── /curated/payments.parquet     (normalisés)

   Gold Layer (Aggregated)
   ├── /aggregates/daily_revenue.parquet
   ├── /aggregates/top_products.parquet
   ├── /aggregates/fraud_stats.parquet
   └── /aggregates/customer_lifetime_value.parquet
   ```

2. **Pipeline ETL/ELT (Airflow + dbt)**

   - **DAG quotidien** (2h du matin)

     1. Extract : PostgreSQL → Parquet (Bronze)
     2. Extract : MongoDB → Parquet (Bronze)
     3. Transform : dbt models (Bronze → Silver)
     4. Aggregate : dbt models (Silver → Gold)
     5. Test : dbt tests qualité
     6. Load : Upload MinIO

   - **DAG temps réel** (micro-batch 15 min)
     1. Kafka → Parquet (incremental)
     2. Append Bronze layer

3. **Dashboards BI (Superset)**

   - **Dashboard Exécutif**

     - KPI : CA, nb commandes, panier moyen
     - Tendances : croissance hebdo/mensuelle
     - Alertes : chute CA, pic fraudes

   - **Dashboard Fraude**

     - Taux fraude temps réel
     - Coût fraude évité
     - Top règles déclenchées
     - Analyse géographique

   - **Dashboard Produits**

     - Top produits/catégories
     - Stock faible
     - Produits à forte marge

   - **Dashboard Clients**
     - Segmentation RFM (Recency, Frequency, Monetary)
     - Taux rétention
     - Customer Lifetime Value

### ✅ Statut actuel : **20% FAIT**

- ✅ MinIO installé
- ✅ Parquet files disponibles (dataset)
- ✅ 3 vues SQL PostgreSQL
- ❌ Buckets Bronze/Silver/Gold pas créés
- ❌ Airflow pas installé
- ❌ dbt pas configuré
- ❌ Superset pas installé

---

## 🔌 PILIER 5 : EXPOSITION - API & SERVICES EXTERNES

### 🎯 Objectifs métier

- **Exigence #5** : Accès simple données via service standardisé
- **Contrainte** : Multiplicité sources + besoin accès externe

### 🔧 Technologies

- **FastAPI 0.109** (framework REST moderne)
- **Swagger/OpenAPI** (documentation auto)
- **JWT** (authentification tokens)
- **Redis** (cache réponses)

### 📋 Livrables

1. **API RESTful complète**

   ```
   # CRUD Clients
   GET    /api/v1/customers
   GET    /api/v1/customers/{id}
   POST   /api/v1/customers
   PUT    /api/v1/customers/{id}
   DELETE /api/v1/customers/{id}

   # Commandes
   GET    /api/v1/orders?status=paid&limit=100
   GET    /api/v1/orders/{id}
   POST   /api/v1/orders

   # Paiements
   GET    /api/v1/payments?is_fraudulent=true
   GET    /api/v1/payments/{id}

   # Fraude
   GET    /api/v1/fraud-alerts
   POST   /api/v1/fraud-alerts/check   (scoring temps réel)

   # Analytics (cache 5 min)
   GET    /api/v1/analytics/revenue?start_date=2025-01-01
   GET    /api/v1/analytics/top-products?limit=10
   GET    /api/v1/analytics/fraud-rate

   # Vérification identité (IA)
   POST   /api/v1/verify-identity
          Body: {image: base64, customer_id: "C00001"}
          Response: {is_adult: true, confidence: 0.95, ...}
   ```

2. **Authentification & Sécurité**

   - JWT tokens (expiration 1h)
   - API Keys pour partenaires
   - Rate limiting (100 req/min/user)
   - CORS configuré
   - HTTPS obligatoire (prod)

3. **Documentation interactive**

   - Swagger UI auto-générée
   - Exemples requêtes/réponses
   - Codes erreurs détaillés
   - Tutoriels intégration

4. **Performance**
   - Cache Redis (analytics, top products)
   - Pagination automatique (max 1000 résultats)
   - Compression gzip
   - Indexation DB optimale

### ✅ Statut actuel : **0% FAIT**

- ❌ FastAPI pas installé
- ❌ Aucun endpoint créé
- ❌ Pas de documentation API

---

## 🤖 PILIER 6 : IA & CONFORMITÉ - RECONNAISSANCE CNI

### 🎯 Objectifs métier

- **Exigence #11** : Modèle reconnaissance carte d'identité pour ventes adultes
- **Contrainte légale** : Contrôle automatique documents identité

### 🔧 Technologies

- **TensorFlow 2.15** (deep learning)
- **OpenCV** (preprocessing images)
- **Tesseract OCR** (extraction texte)
- **MLflow** (versioning modèles)

### 📋 Livrables

1. **Dataset entraînement**

   - 60 images synthétiques (PNG 300 DPI)
   - Labels : nom, prénom, sexe, date naissance, numéro doc
   - Augmentation : rotation, blur, luminosité (×10 = 600 images)
   - Split : 70% train, 15% validation, 15% test

2. **Pipeline ML**

   ```
   Étape 1 : Preprocessing
   ├── Détection contours carte (OpenCV)
   ├── Redressement perspective
   ├── Normalisation taille (800×600)
   └── Conversion grayscale

   Étape 2 : Extraction texte (Tesseract OCR)
   ├── Zones ROI (nom, prénom, date naissance)
   ├── Correction orthographique
   └── Validation format dates

   Étape 3 : Vérification cohérence
   ├── Calcul âge depuis date naissance
   ├── Validation numéro document (checksum)
   ├── Détection fraude (photo floue, document expiré)
   └── Score confiance (0-1)
   ```

3. **Modèle CNN (architecture)**

   - Input : image 800×600×3
   - Convolution layers : 3×3, 64→128→256 filters
   - MaxPooling 2×2
   - Dense layers : 512→256
   - Output : classification binaire (is_adult)
   - Loss : Binary Cross-Entropy
   - Optimizer : Adam (lr=0.001)

4. **Intégration production**

   - Endpoint FastAPI `/verify-identity`
   - Upload image (max 5 MB)
   - Temps réponse < 2s
   - Logging toutes vérifications (audit trail)
   - Stockage images MinIO (chiffrées)

5. **Monitoring modèle**
   - Accuracy, Precision, Recall (dashboard)
   - Distribution scores confiance
   - Taux faux positifs/négatifs
   - Alertes dégradation performance

### ✅ Statut actuel : **10% FAIT**

- ✅ 60 images + labels disponibles
- ✅ Table identity_verifications créée
- ❌ Modèle TensorFlow pas entraîné
- ❌ Pipeline preprocessing pas codé
- ❌ API prédiction pas créée

---

## 🎯 PILIER TRANSVERSE : SCALABILITÉ & HAUTE DISPONIBILITÉ

### 🎯 Objectifs métier

- **Exigence #7** : Garantir scalabilité face à croissance
- **Exigence #8** : Garantir continuité service (résilience)

### 📋 Stratégies implémentées

#### 1️⃣ **Scalabilité horizontale**

- Kafka : 3 brokers (ajout brokers sans downtime)
- Flink : TaskManagers scalables (parallélisme configurable)
- PostgreSQL : Read replicas (lecture distribuée)
- MinIO : Distributed mode (multi-nodes)
- FastAPI : Gunicorn multi-workers (auto-scaling)

#### 2️⃣ **Haute disponibilité**

- Kafka replication factor = 3 (tolérance 2 pannes)
- PostgreSQL streaming replication (failover auto)
- MongoDB replica set 3 nodes (élection primaire)
- Zookeeper ensemble 3 nodes (quorum)
- Healthchecks Docker (restart automatique)

#### 3️⃣ **Monitoring & Observabilité**

- **Prometheus** : métriques infrastructure

  - CPU, RAM, disk, network (node-exporter)
  - Métriques PostgreSQL (postgres-exporter)
  - Métriques Kafka (JMX exporter)
  - Métriques custom (FastAPI)

- **Grafana** : dashboards temps réel

  - Dashboard infrastructure
  - Dashboard applications
  - Dashboard business (KPI)
  - Alertes (Slack, email)

- **Logs centralisés** (bonus)
  - ELK Stack : Elasticsearch + Logstash + Kibana
  - Collecte logs Docker containers
  - Corrélation traces (trace_id)

#### 4️⃣ **Disaster Recovery**

- Backup PostgreSQL quotidien (pg_dump)
- Snapshot MinIO hebdomadaire
- Configuration as Code (Git)
- Restore testé mensuellement

### ✅ Statut actuel : **75% FAIT**

- ✅ Kafka 3 brokers HA
- ✅ Prometheus + Grafana installés
- ✅ Healthchecks Docker
- ⏳ Backup automatique à configurer
- ⏳ Logs centralisés (optionnel)

---

## 📊 RÉCAPITULATIF - MATRICE PILIERS × EXIGENCES

| Exigence                           | Pilier 1 | Pilier 2 | Pilier 3 | Pilier 4 | Pilier 5 | Pilier 6 | Transverse |
| ---------------------------------- | -------- | -------- | -------- | -------- | -------- | -------- | ---------- |
| **#1** Stockage fiable             | ✅ 100%  | -        | -        | -        | -        | -        | -          |
| **#2** Événements utilisateurs     | -        | ⏳ 30%   | -        | -        | -        | -        | -          |
| **#3** Data Lake centralisé        | -        | -        | -        | ⏳ 20%   | -        | -        | -          |
| **#4** Détection fraude temps réel | -        | -        | ⏳ 10%   | -        | -        | -        | -          |
| **#5** API exposition              | -        | -        | -        | -        | ❌ 0%    | -        | -          |
| **#6** BI rapide                   | -        | -        | -        | ⏳ 25%   | -        | -        | -          |
| **#7** Scalabilité                 | -        | -        | -        | -        | -        | -        | ✅ 80%     |
| **#8** Haute disponibilité         | -        | -        | -        | -        | -        | -        | ✅ 75%     |
| **#9** Conformité sécurité         | ✅ 70%   | -        | -        | -        | -        | -        | ⏳ 60%     |
| **#10** Qualité données            | ✅ 60%   | -        | -        | ⏳ 30%   | -        | -        | -          |
| **#11** IA reconnaissance CNI      | -        | -        | -        | -        | -        | ⏳ 10%   | -          |

---

## 🗓️ ROADMAP PAR PILIER (7 semaines)

### **Semaine 1-2 : PILIER 2 (Streaming)**

- ✅ Charger events.jsonl → MongoDB
- ✅ Créer topics Kafka
- ✅ Coder producers/consumers Python
- **Livrable** : 71k événements streamés en temps réel

### **Semaine 2-3 : PILIER 3 (Fraude)**

- ✅ Configurer Flink
- ✅ Implémenter 5 règles détection
- ✅ Enrichissement PostgreSQL
- **Livrable** : Alertes fraude temps réel opérationnelles

### **Semaine 3-4 : PILIER 5 (API)**

- ✅ Installer FastAPI
- ✅ Créer 15+ endpoints REST
- ✅ Documentation Swagger
- **Livrable** : API RESTful complète et documentée

### **Semaine 4-5 : PILIER 4 (Data Lake)**

- ✅ Créer buckets MinIO (Bronze/Silver/Gold)
- ✅ Installer Airflow + dbt
- ✅ DAG ETL quotidien
- **Livrable** : Pipeline ETL/ELT automatisé

### **Semaine 5-6 : PILIER 4 (BI)**

- ✅ Installer Superset
- ✅ Créer 4 dashboards
- ✅ Alertes automatiques
- **Livrable** : BI décisionnel opérationnel

### **Semaine 6-7 : PILIER 6 (IA)**

- ✅ Entraîner modèle TensorFlow
- ✅ API prédiction CNI
- ✅ Tests utilisateurs
- **Livrable** : Vérification identité automatique

### **Semaine 7 : PILIER 1 & Transverse (Finalisation)**

- ✅ Tests qualité dbt
- ✅ Backup automatique
- ✅ Logs centralisés (bonus)
- **Livrable** : Solution production-ready

---

## 🎯 LIVRABLES FINAUX DU PROJET

### 📦 **Livrables techniques**

1. Infrastructure Docker Compose (11+ services)
2. Base PostgreSQL (8 tables, 16k+ lignes)
3. Pipeline streaming Kafka + Flink
4. Data Lake MinIO (Bronze/Silver/Gold)
5. API REST FastAPI (20+ endpoints)
6. Dashboards BI Superset (4 dashboards)
7. Modèle IA TensorFlow (reconnaissance CNI)
8. Pipeline ETL Airflow + dbt
9. Monitoring Prometheus + Grafana
10. Documentation complète (30+ pages)

### 📄 **Livrables documentation**

1. Architecture technique détaillée
2. Guide d'installation et démarrage
3. Documentation API (Swagger)
4. Dictionnaire de données
5. Runbook opérationnel (troubleshooting)
6. Rapport de tests (unitaires, intégration, charge)
7. Plan de reprise d'activité (PRA)
8. Politique RGPD et sécurité

### 🎬 **Livrables présentation**

1. Slides exécutifs (15 slides max)
2. Démonstration live (15 min)
3. Vidéo récapitulative (5 min)

---

## 📈 INDICATEURS DE SUCCÈS (KPI)

| Pilier           | KPI                        | Objectif   | Actuel   |
| ---------------- | -------------------------- | ---------- | -------- |
| **1. Stockage**  | Temps requête moyenne      | <100ms     | ✅ 45ms  |
| **2. Streaming** | Throughput Kafka           | >10k msg/s | ⏳ 0     |
| **3. Fraude**    | Taux détection             | >90%       | ⏳ 0%    |
| **3. Fraude**    | Faux positifs              | <5%        | ⏳ N/A   |
| **4. Data Lake** | Taille données             | >100 GB    | ⏳ 27 MB |
| **4. BI**        | Temps chargement dashboard | <3s        | ⏳ N/A   |
| **5. API**       | Latence p95                | <200ms     | ❌ N/A   |
| **5. API**       | Disponibilité              | >99.5%     | ❌ N/A   |
| **6. IA**        | Accuracy CNI               | >95%       | ⏳ 0%    |
| **Transverse**   | Uptime global              | >99.9%     | ✅ 100%  |

---

## 🎓 COMPÉTENCES TECHNIQUES DÉMONTRÉES

✅ **Data Engineering**

- Modélisation relationnelle (PostgreSQL)
- Modélisation NoSQL (MongoDB)
- Stream processing (Kafka, Flink)
- Batch processing (Airflow, dbt)
- Data Lake architecture (MinIO, Parquet)

✅ **DevOps & Infrastructure**

- Containerisation (Docker Compose)
- Orchestration (Kubernetes bonus)
- Monitoring (Prometheus, Grafana)
- CI/CD (Git, GitHub Actions bonus)

✅ **Data Science & IA**

- Machine Learning (fraude)
- Deep Learning (CNN, TensorFlow)
- Computer Vision (OCR)
- MLOps (MLflow, versioning)

✅ **Backend Development**

- API REST (FastAPI, Swagger)
- Authentification (JWT)
- Performance (cache, indexation)

✅ **Business Intelligence**

- Dashboards (Superset)
- Métriques business (KPI)
- Data visualization

---

**📅 Date de livraison prévue** : 24 mars 2026 (7 semaines)  
**👤 Responsable projet** : Pierre Chevalier & Jean Macario
**🎯 Score objectif** : 105/110 points (96%)
