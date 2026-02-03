# 📊 Analyse Complète du Dataset KiVendTout

## 🎯 Vue d'Ensemble

Le dataset KiVendTout est un **dataset e-commerce synthétique complet** conçu pour simuler une plateforme de vente en ligne avec :
- **Détection de fraude** : Labels de fraude, alertes, patterns suspects
- **Tracking comportemental** : 71,694 événements utilisateurs
- **Vérification d'identité** : 60 cartes d'identité synthétiques avec labels
- **Architecture multi-formats** : CSV (relationnel), Parquet (analytique), JSONL (streaming)

---

## 📁 Structure Complète du Dataset

### 🗂️ Fichiers Disponibles

```
kivendtout_dataset/
├── customers.csv + customers.parquet          # 2,500 clients
├── products.csv + products.parquet            # 200 produits
├── orders.csv + orders.parquet                # 1,289 commandes
├── order_items.csv + order_items.parquet      # 2,651 lignes de commande
├── payments.csv + payments.parquet            # 1,583 paiements (avec labels fraude)
├── sessions.csv + sessions.parquet            # 6,000 sessions web
├── fraud_alerts.csv + fraud_alerts.parquet    # 22 alertes de fraude
├── events.jsonl + events.parquet              # 71,694 événements comportementaux
├── synthetic_id_labels.csv                    # 60 labels de cartes d'identité
└── synthetic_id_cards/                        # 60 images PNG de cartes d'identité
    ├── id_0000.png → id_0059.png
```

**Total : 86,005 lignes de données + 60 images**

---

## 📋 Description Détaillée des Tables

### 1️⃣ **customers.csv** (2,500 lignes)
**Rôle** : Données des clients inscrits sur la plateforme

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| `customer_id` | STRING (PK) | Identifiant unique client | `C00001` |
| `signup_ts` | TIMESTAMP | Date d'inscription | `2025-11-26 08:10:15` |
| `country` | STRING | Pays de résidence (ISO 2) | `BE`, `GB`, `FR` |
| `preferred_device` | STRING | Device préféré | `web_mobile`, `ios`, `android` |
| `birthdate` | DATE | Date de naissance | `1973-09-15` |
| `is_minor` | BOOLEAN | Client mineur (< 18 ans) | `0` ou `1` |

**Insights** :
- Distribution géographique multi-pays (EU principalement)
- Permet validation d'âge pour produits restreints (alcool, etc.)
- Device tracking pour analyse cross-device

---

### 2️⃣ **products.csv** (200 lignes)
**Rôle** : Catalogue produits avec restrictions d'âge

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| `product_id` | STRING (PK) | Identifiant unique produit | `P0001` |
| `name` | STRING | Nom du produit | `Product 0001` |
| `category` | STRING | Catégorie principale | `Sports`, `Fashion`, `Electronics` |
| `is_adult_restricted` | BOOLEAN | Restriction d'âge (+18) | `0` ou `1` |
| `unit_price` | DECIMAL | Prix unitaire en EUR | `16.69` |
| `created_at` | TIMESTAMP | Date de création | `2025-11-08 15:46:54` |

**Insights** :
- Produits adultes nécessitent vérification d'identité
- Prix variant de ~10€ à ~100€
- Catégories diversifiées (Sports, Fashion, Electronics, Home, etc.)

---

### 3️⃣ **orders.csv** (1,289 lignes)
**Rôle** : Commandes passées par les clients

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| `order_id` | STRING (PK) | Identifiant unique commande | `O0000001` |
| `customer_id` | STRING (FK) | Client ayant passé la commande | `C02452` |
| `session_id` | STRING (FK) | Session web associée | `S000009` |
| `payment_id` | STRING (FK) | Paiement lié | `PAY0000002` |
| `order_ts` | TIMESTAMP | Date/heure de la commande | `2025-11-17 06:38:34` |
| `total_amount` | DECIMAL | Montant total TTC | `47.83` |
| `currency` | STRING | Devise (toujours EUR) | `EUR` |
| `shipping_method` | STRING | Mode de livraison | `express`, `standard` |
| `status` | STRING | Statut commande | `paid`, `cancelled`, `pending` |

**Insights** :
- Lien fort entre session → paiement → commande
- Permet tracking du funnel complet
- Statuts : `paid` (majoritaire), `cancelled`, `pending`

---

### 4️⃣ **order_items.csv** (2,651 lignes)
**Rôle** : Lignes de commande (détail des produits commandés)

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| `order_id` | STRING (FK) | Commande parente | `O0000001` |
| `product_id` | STRING (FK) | Produit commandé | `P0044` |
| `qty` | INTEGER | Quantité commandée | `1`, `2`, `3` |

**Insights** :
- Panier moyen : ~2.05 produits par commande (2651/1289)
- Quantités généralement faibles (1-3 unités)
- **⚠️ Pas de `unit_price` ici** → À récupérer depuis `products`

---

### 5️⃣ **payments.csv** (1,583 lignes) 🔴 **LABELS FRAUDE**
**Rôle** : Tentatives de paiement avec labels de fraude

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| `payment_id` | STRING (PK) | Identifiant paiement | `PAY0000001` |
| `customer_id` | STRING (FK) | Client payeur | `C00695` |
| `session_id` | STRING (FK) | Session de paiement | `S000001` |
| `attempt_ts` | TIMESTAMP | Horodatage tentative | `2025-11-11 09:51:23` |
| `method` | STRING | Méthode paiement | `card`, `paypal`, `bank_transfer` |
| `card_bin` | STRING | BIN carte bancaire (6 digits) | `492878` |
| `payment_country` | STRING | Pays paiement (IP géoloc) | `IT`, `DE`, `FR` |
| `ip_hash` | STRING | Hash anonymisé IP | `7f19717dd0b54b37` |
| `device_id` | STRING | ID device (fingerprint) | `dev_38b70bd879a5` |
| `amount` | DECIMAL | Montant paiement | `58.58` |
| `result` | STRING | Résultat paiement | `success`, `failed` |
| `is_fraud_label` | BOOLEAN | **LABEL FRAUDE** (ground truth) | `0` ou `1` |

**Insights** :
- **~100 paiements frauduleux labellés** (à valider)
- BIN carte pour détecter pays émetteur
- `payment_country` vs `customer.country` → détection mismatch géographique
- Device ID permet détecter changements suspects

---

### 6️⃣ **sessions.csv** (6,000 lignes)
**Rôle** : Sessions de navigation web

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| `session_id` | STRING (PK) | Identifiant session | `S000001` |
| `customer_id` | STRING (FK) | Client (NULL si anonyme) | `C00695` |
| `start_ts` | TIMESTAMP | Début session | `2025-11-19 14:23:04` |
| `end_ts` | TIMESTAMP | Fin session | `2025-11-19 14:39:04` |
| `device` | STRING | Type device | `web_desktop`, `web_mobile`, `ios`, `android` |
| `ip_hash` | STRING | Hash IP | `7f19717dd0b54b37` |
| `utm_source` | STRING | Source marketing | `direct`, `ads_meta`, `ads_google` |
| `utm_campaign` | STRING | Campagne marketing | `none`, nom campagne |

**Insights** :
- Durée session : calcul `end_ts - start_ts`
- Attribution marketing via UTM
- Permet détecter sessions suspectes (durée anormale, etc.)

---

### 7️⃣ **fraud_alerts.csv** (22 lignes) 🚨 **ALERTES FRAUDE**
**Rôle** : Alertes générées par règles de détection

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| `alert_id` | STRING (PK) | ID alerte unique | `AL34313390CF` |
| `alert_ts` | TIMESTAMP | Date/heure alerte | `2025-11-11 09:51:23` |
| `payment_id` | STRING (FK) | Paiement suspect | `PAY0000001` |
| `customer_id` | STRING (FK) | Client concerné | `C00695` |
| `session_id` | STRING (FK) | Session concernée | `S000001` |
| `amount` | DECIMAL | Montant transaction | `58.58` |
| `rule_triggered` | STRING | **Règle détectée** | `high_amount`, `country_mismatch` |
| `is_fraud_label` | BOOLEAN | Confirmation fraude | `1` |

**Règles de fraude détectées** :
- `high_amount` : Montant anormalement élevé
- `country_mismatch` : Pays paiement ≠ pays client
- `velocity` : Trop de tentatives rapides
- `device_change` : Changement device suspect

**Insights** :
- **22 alertes confirmées** (tous `is_fraud_label = 1`)
- Corrélation forte avec `payments.is_fraud_label`
- Base pour entraîner modèle ML

---

### 8️⃣ **events.jsonl** (71,694 lignes) 🎬 **STREAMING EVENTS**
**Rôle** : Événements comportementaux en temps réel

**Format** : JSON Lines (1 event par ligne)

**Schema JSON** :
```json
{
  "event_id": "UUID",
  "ts": "TIMESTAMP ISO8601",
  "event_type": "TYPE",  // voir ci-dessous
  "customer_id": "C00001",
  "session_id": "S000001",
  "device": "web_desktop",
  "ip_hash": "HASH",
  "utm_source": "direct",
  "utm_campaign": "none",
  "product_id": "P0185",  // NULL si pas applicable
  "cart_value": 101.90,   // NULL si pas applicable
  "payment_id": "PAY001", // NULL si pas applicable
  "order_id": "O0001"     // NULL si pas applicable
}
```

**Types d'événements** :
- `product_view` : Consultation produit
- `add_to_cart` : Ajout panier
- `remove_from_cart` : Retrait panier
- `search` : Recherche produit
- `payment_attempt` : Tentative paiement
- `order_placed` : Commande validée
- `checkout_start` : Début checkout

**Insights** :
- **71,694 événements** sur ~2 mois (Nov-Déc 2025)
- Permet reconstruire le parcours client complet
- Détection d'anomalies comportementales (vitesse, patterns)
- **Idéal pour Kafka streaming + Flink processing**

---

### 9️⃣ **synthetic_id_labels.csv** (60 lignes) 🪪 **CARTES IDENTITÉ**
**Rôle** : Labels pour reconnaissance OCR/Computer Vision

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| `last_name` | STRING | Nom de famille | `RICHARD` |
| `first_name` | STRING | Prénom | `JEAN` |
| `sex` | CHAR | Sexe (M/F) | `M` |
| `birthdate` | DATE | Date naissance | `1989-09-21` |
| `doc_number` | STRING | Numéro document | `ID2288937` |
| `expiry` | DATE | Date expiration | `2035-09-07` |
| `is_adult` | BOOLEAN | Majeur (≥18 ans) | `1` |
| `file` | STRING | Nom fichier image | `id_0000.png` |

**Images** : 60 PNG dans `synthetic_id_cards/`

**Use case** :
- Entraîner modèle TensorFlow/OpenCV pour OCR
- Valider âge automatiquement pour produits restreints
- **Bloc 4 du sujet** : Computer Vision

---

## 🔗 Relations Entre Tables

```
customers (2500)
    ├──→ sessions (6000) ─→ events.jsonl (71k)
    ├──→ orders (1289)
    │       ├──→ order_items (2651) ──→ products (200)
    │       └──→ payments (1583)
    └──→ payments (1583)
            └──→ fraud_alerts (22)
```

**Clés étrangères** :
- `orders.customer_id` → `customers.customer_id`
- `orders.session_id` → `sessions.session_id`
- `orders.payment_id` → `payments.payment_id`
- `order_items.order_id` → `orders.order_id`
- `order_items.product_id` → `products.product_id`
- `payments.customer_id` → `customers.customer_id`
- `payments.session_id` → `sessions.session_id`
- `fraud_alerts.payment_id` → `payments.payment_id`
- `events (JSON).customer_id` → `customers.customer_id`
- `events (JSON).session_id` → `sessions.session_id`

---

## 📊 Statistiques Clés

| Métrique | Valeur | Calcul |
|----------|--------|--------|
| **Clients** | 2,500 | - |
| **Produits** | 200 | - |
| **Sessions** | 6,000 | - |
| **Commandes** | 1,289 | - |
| **Paiements** | 1,583 | (plus que commandes → échecs/rejets) |
| **Lignes commande** | 2,651 | - |
| **Événements** | 71,694 | - |
| **Alertes fraude** | 22 | - |
| **Images ID** | 60 | - |
| **Panier moyen** | ~2.05 produits | 2651 / 1289 |
| **CA Total estimé** | ~60-80k€ | sum(orders.total_amount) |
| **Taux fraude** | ~6-8% | fraud / total_payments |
| **Sessions/client** | 2.4 | 6000 / 2500 |

---

## 🎯 Utilisation par Technologie du Projet

### 🐘 **PostgreSQL** (OLTP)
**Tables à ingérer** :
- ✅ `customers.csv`
- ✅ `products.csv`
- ✅ `orders.csv`
- ✅ `order_items.csv`
- ✅ `payments.csv`
- ✅ `sessions.csv`
- ✅ `fraud_alerts.csv`

**Usage** :
- Données transactionnelles ACID
- Jointures SQL pour analytics
- Vues matérialisées pour performance

---

### 🍃 **MongoDB** (NoSQL)
**Collections à créer** :
- `events` : Import depuis `events.jsonl` (71k documents)
- `customer_profiles` : Agrégations enrichies
- `fraud_patterns` : Patterns détectés par ML

**Usage** :
- Stockage flexible événements JSON
- Requêtes temporelles sur `ts`
- Agrégations MongoDB pour analytics comportementales

---

### 📦 **MinIO (Data Lake)**
**Bronze Layer** (raw data) :
- Tous les `.parquet` (format columnar optimisé)
- `events.parquet` (71k events)
- `synthetic_id_cards/*.png` (60 images)

**Silver Layer** (cleaned) :
- Parquets nettoyés et validés

**Gold Layer** (aggregated) :
- Tables agrégées pour BI (par jour, par produit, etc.)

**Usage** :
- Archivage long terme
- Source pour traitements batch (Spark, dbt)
- Storage images pour ML

---

### 🎬 **Kafka** (Streaming)
**Topics à créer** :
- `user-events` : Stream depuis `events.jsonl` (replay historique)
- `payments` : Stream paiements en temps réel
- `fraud-alerts` : Alertes détectées par Flink
- `orders` : Commandes validées

**Usage** :
- Simulation flux temps réel
- Ingestion continue vers Flink
- Replay historique pour tests

---

### ⚡ **Flink** (Stream Processing)
**Sources** :
- Kafka topics (`user-events`, `payments`)

**Processing** :
- Détection fraude temps réel (règles + ML)
- Agrégations windowed (nb events / 5min)
- Enrichissement avec PostgreSQL/MongoDB

**Sinks** :
- Kafka (`fraud-alerts`)
- PostgreSQL (`fraud_alerts` table)

---

### 🤖 **TensorFlow** (ML/CV)
**Datasets** :
- `synthetic_id_cards/*.png` (60 images)
- `synthetic_id_labels.csv` (labels pour supervised learning)
- `payments.csv` (`is_fraud_label` pour classification binaire)

**Modèles** :
1. **OCR ID Cards** : CNN pour extraction texte
2. **Fraud Detection** : Random Forest / XGBoost sur features paiements
3. **Age Verification** : Classification date naissance depuis ID

---

### 📊 **Superset** (BI)
**Datasources** :
- PostgreSQL (toutes tables)
- MinIO/Parquet via Trino/Presto

**Dashboards à créer** :
- CA par jour/semaine/mois
- Top produits vendus
- Taux de fraude (KPI)
- Funnel conversion (sessions → orders)
- Origine trafic (UTM analysis)

---

## 🚀 Stratégie d'Ingestion Complète

### **Phase 1 : PostgreSQL** (Tables relationnelles)
```bash
1. customers.csv       → customers (2500 rows)
2. products.csv        → products (200 rows)
3. sessions.csv        → sessions (6000 rows)
4. orders.csv          → orders (1289 rows)
5. order_items.csv     → order_items (2651 rows)
6. payments.csv        → payments (1583 rows)
7. fraud_alerts.csv    → fraud_alerts (22 rows)
```

### **Phase 2 : MongoDB** (Documents JSON)
```bash
mongoimport --db kivendtout --collection events \
  --file events.jsonl --jsonArray=false
```

### **Phase 3 : MinIO** (Data Lake)
```bash
# Bronze layer
mc cp *.parquet minio/kivendtout-bronze/
mc cp synthetic_id_cards/*.png minio/kivendtout-bronze/id_cards/
```

### **Phase 4 : Kafka** (Streaming simulation)
```python
# Producer Python : lire events.jsonl et publier dans Kafka
# avec timestamps réels ou replay accéléré
```

---

## 🎯 Points Clés pour le Projet

### ✅ **Forces du Dataset**
1. **Multi-formats** : CSV/Parquet/JSON → teste toutes techno
2. **Labels fraude** : Ground truth pour ML supervisé
3. **Richesse relationnelle** : 7 tables liées
4. **Volume réaliste** : 86k lignes → assez pour tests, pas trop pour dev
5. **Images synthétiques** : 60 ID cards pour CV
6. **Streaming ready** : 71k events pour Kafka/Flink

### ⚠️ **Points d'Attention**
1. **Colonnes différentes** : `qty` vs `quantity`, vérifier tous les CSV
2. **Pas de prices dans order_items** : Joindre avec `products.unit_price`
3. **Formats dates** : Vérifier parsing (`YYYY-MM-DD HH:MM:SS`)
4. **Parquet vs CSV** : Parquet plus performant mais nécessite libs (pandas, pyarrow)
5. **JSONL streaming** : 71k lignes = ~20MB → tester mémoire

---

## 📝 TODO Script d'Ingestion

**✅ À implémenter dans `load_data_to_postgres.py`** :

1. ✅ Charger `customers.csv`
2. ✅ Charger `products.csv`
3. ✅ Charger `sessions.csv` (nouveau)
4. ✅ Charger `orders.csv`
5. ✅ Charger `order_items.csv` (fixer `qty`, joindre `products.unit_price`)
6. ✅ Charger `payments.csv` (nouveau, avec labels fraude)
7. ✅ Charger `fraud_alerts.csv` (nouveau)
8. ✅ Validation intégrité référentielle
9. ✅ Statistiques finales (CA, fraude, etc.)

**📦 Bonus** :
- Script MongoDB : `load_data_to_mongodb.py` pour `events.jsonl`
- Script MinIO : `upload_to_minio.py` pour Parquets + images
- Script Kafka Producer : `stream_events_to_kafka.py`

---

## 🏆 Conclusion

Le dataset KiVendTout est **parfaitement adapté au sujet M1 Data Engineering** :

✅ Couvre **tous les use cases** du projet (OLTP, NoSQL, Streaming, ML, BI)  
✅ Volume **suffisant** pour démontrer scalabilité  
✅ **Labels fraude** pour ML supervisé  
✅ **Multi-formats** (CSV, Parquet, JSON, Images)  
✅ **Relations complexes** pour tester jointures SQL  
✅ **Events streaming** pour Kafka + Flink  
✅ **Images synthétiques** pour Computer Vision  

🎯 **Prochaines étapes** :
1. Refaire script ingestion PostgreSQL complet
2. Ajouter ingestion MongoDB (events.jsonl)
3. Uploader Parquet vers MinIO
4. Créer producer Kafka pour streaming

---

📅 **Dernière mise à jour** : 3 février 2026  
👤 **Auteur** : Pierre Chevalier - M1 Data Engineering EFREI
