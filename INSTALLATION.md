# 🚀 Guide d'Installation - PATATOR

## 📋 Pré-requis

Avant de lancer Patator, assurez-vous d'avoir :

### Obligatoires
- ✅ **Docker Desktop** (ou Docker Engine + Docker Compose)
- ✅ **Python 3.8+**
- ✅ **Git**

### Vérification
```bash
# Docker
docker --version
docker compose version

# Python
python3 --version

# Git
git --version
```

---

## 📥 Installation

### 1. Cloner le Projet
```bash
git clone https://github.com/ChevalierPierree/ProjetDataM1JeanPierre.git
cd ProjetDataM1JeanPierre
git checkout PierreDump
```

### 2. Installer les Dépendances Python
```bash
pip3 install -r requirements.txt

# Ou manuellement :
pip3 install kafka-python psycopg2-binary pymongo fastapi uvicorn pydantic apache-flink
```

### 3. Rendre le Script Exécutable
```bash
chmod +x patator
```

---

## 🚀 Lancement Rapide

### Option 1 : Script Patator (Recommandé)
```bash
./patator
```

C'est tout ! Le script va :
1. ✅ Vérifier les pré-requis
2. ✅ Démarrer les 13 services Docker
3. ✅ Charger les données (PostgreSQL + MongoDB)
4. ✅ Configurer Kafka et streamer 71,694 événements
5. ✅ Lancer la détection de fraude
6. ✅ Démarrer l'API Backend (port 8000)
7. ✅ Démarrer le Dashboard Web (port 7600)
8. ✅ Ouvrir le dashboard dans votre navigateur

**Durée totale** : ~3-5 minutes ⏱️

---

### Option 2 : Alias Global (Optionnel)

Pour taper juste `patator` n'importe où :

#### macOS / Linux (bash)
```bash
echo 'alias patator="/Users/pierrechevalier/Desktop/PERSO/EFREI/M1 DATA/Patator/patator"' >> ~/.bash_profile
source ~/.bash_profile
```

#### macOS / Linux (zsh)
```bash
echo 'alias patator="/Users/pierrechevalier/Desktop/PERSO/EFREI/M1 DATA/Patator/patator"' >> ~/.zshrc
source ~/.zshrc
```

Maintenant vous pouvez taper `patator` depuis n'importe quel dossier !

---

## 🖥️ Accès aux Services

Une fois lancé, vous aurez accès à :

### 🎯 Principal
| Service | URL | Description |
|---------|-----|-------------|
| **Dashboard Web** | http://localhost:7600/fraud_dashboard.html | Interface analyst pour gérer les alertes |
| **API Backend** | http://localhost:8000 | API REST pour le dashboard |

### 🔧 Monitoring
| Service | URL | Description |
|---------|-----|-------------|
| Kafka UI | http://localhost:8082 | Interface pour Kafka (topics, messages) |
| Flink Web UI | http://localhost:8083 | Monitoring Flink jobs |
| Grafana | http://localhost:4000 | Dashboards de monitoring |
| Prometheus | http://localhost:9090 | Métriques système |

---

## 🛑 Arrêter les Services

### Arrêter tout
```bash
cd /chemin/vers/Patator
docker compose down
```

### Arrêter + Supprimer les données
```bash
docker compose down -v
```

---

## 🔍 Vérifications

### Vérifier les services Docker
```bash
docker compose ps
```

Vous devriez voir 13 services `Up` :
- postgres
- mongodb
- kafka-1, kafka-2, kafka-3
- zookeeper
- flink-jobmanager
- flink-taskmanager
- minio
- kafka-ui
- prometheus
- grafana
- postgres-exporter

### Vérifier l'API
```bash
curl http://localhost:8000/health
# Devrait retourner : {"status":"healthy"}
```

### Vérifier les stats
```bash
curl http://localhost:8000/api/stats | jq .
```

---

## 📊 Logs

### Consulter les logs
```bash
# API Backend
tail -f logs/fraud_dashboard_api.log

# Détection de fraude
tail -f logs/fraud_detection.log

# Dashboard HTTP
tail -f logs/http_server.log

# Docker services
docker compose logs -f kafka-1
docker compose logs -f postgres
```

---

## 🐛 Problèmes Courants

### Port déjà utilisé
```bash
# Libérer le port 8000 (API)
lsof -ti:8000 | xargs kill -9

# Libérer le port 7600 (Dashboard)
lsof -ti:7600 | xargs kill -9
```

### Kafka ne démarre pas
```bash
# Redémarrer les brokers Kafka
docker compose restart kafka-1 kafka-2 kafka-3 zookeeper
```

### PostgreSQL sans données
```bash
# Recharger les données
python3 scripts/load_data_to_postgres.py
```

### MongoDB sans données
```bash
# Recharger les événements
python3 scripts/load_events_to_mongodb.py
```

### Kafka sans messages
```bash
# Re-streamer les événements
python3 scripts/stream_events_to_kafka.py
```

---

## 🔄 Réinitialiser Complètement

Pour repartir de zéro :

```bash
# 1. Arrêter et supprimer tout
docker compose down -v

# 2. Supprimer les logs
rm -rf logs/*

# 3. Relancer
./patator
```

---

## 📖 Documentation

- 📘 **README Principal** : `README.md`
- 📗 **Architecture** : `ARCHITECTURE_PILIERS.md`
- 📙 **Guide Dashboard** : `FRAUD_DASHBOARD_README.md`
- 📕 **Récapitulatif Complet** : `RECAP_COMPLET_PROJET.md`
- 📓 **Explication Fraud Rate** : `EXPLICATION_FRAUD_RATE.md`

---

## 💡 Commandes Utiles

### Démarrage manuel étape par étape
```bash
# 1. Docker
docker compose up -d

# 2. Charger données
python3 scripts/load_data_to_postgres.py
python3 scripts/load_events_to_mongodb.py

# 3. Kafka
python3 scripts/create_kafka_topics.py
python3 scripts/stream_events_to_kafka.py

# 4. Détection fraude
python3 scripts/fraud_detection_realtime.py

# 5. API
python3 api/fraud_dashboard_api.py &

# 6. Dashboard
cd dashboard && python3 -m http.server 7600 &

# 7. Ouvrir le navigateur
open http://localhost:7600/fraud_dashboard.html
```

### Statistiques en temps réel
```bash
# Total alertes
curl -s http://localhost:8000/api/stats | jq '.total_alerts'

# Taux de fraude
curl -s http://localhost:8000/api/stats | jq '.fraud_rate'

# Alertes HIGH
curl -s http://localhost:8000/api/stats | jq '.alerts_by_severity.HIGH'
```

---

## 🎯 Objectif du Projet

**KiVendTout** est une plateforme e-commerce avec un système complet de détection de fraude en temps réel.

### Fonctionnalités
- 🕵️ **11 règles de détection** (basiques + avancées)
- 📊 **Dashboard analyst** pour gérer les alertes
- 🚨 **10,857 alertes** détectées
- ⚡ **Streaming Kafka** (71,694 événements)
- 🐘 **Flink** pour processing distribué
- 📈 **Monitoring** Prometheus + Grafana

### Stack Technique
- Python (FastAPI, Kafka, Flink)
- Docker (13 services)
- PostgreSQL + MongoDB
- Kafka Cluster (3 brokers)
- Apache Flink
- HTML/CSS/JavaScript

---

## 👥 Pour les Nouveaux Utilisateurs

Si vous récupérez ce projet pour la première fois :

1. **Cloner le repo**
   ```bash
   git clone https://github.com/ChevalierPierree/ProjetDataM1JeanPierre.git
   cd ProjetDataM1JeanPierre
   git checkout PierreDump
   ```

2. **Installer les dépendances**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Lancer**
   ```bash
   chmod +x patator
   ./patator
   ```

4. **Profiter !**
   Le dashboard s'ouvre automatiquement : http://localhost:7600/fraud_dashboard.html

---

## 🆘 Support

En cas de problème :

1. Consulter les logs : `tail -f logs/*.log`
2. Vérifier Docker : `docker compose ps`
3. Vérifier les ports : `lsof -i :8000` et `lsof -i :7600`
4. Redémarrer : `docker compose restart`

---

**Auteur** : Pierre Chevalier  
**Projet** : M1 Data Engineering - EFREI  
**Date** : Février 2026  
**Repository** : https://github.com/ChevalierPierree/ProjetDataM1JeanPierre
