# 🎯 PATATOR - Script de Démarrage Automatique

## 📋 Qu'est-ce que PATATOR ?

**PATATOR** est un script bash qui automatise **100% du démarrage** du projet KiVendTout.

En une seule commande, il :
1. ✅ Vérifie les pré-requis (Docker, Python, curl)
2. ✅ Démarre 13 services Docker (Kafka, PostgreSQL, MongoDB, Flink, etc.)
3. ✅ Charge les données (2,500 clients, 100 produits, 71,694 événements)
4. ✅ Configure Kafka (création topics + streaming)
5. ✅ Lance la détection de fraude (génère 10,857 alertes)
6. ✅ Démarre l'API Backend FastAPI (port 8000)
7. ✅ Démarre le Dashboard Web (port 7600)
8. ✅ Ouvre automatiquement le dashboard dans le navigateur

**Durée totale** : 3-5 minutes ⏱️

---

## 🚀 Utilisation

### Lancement
```bash
./patator
```

### Avec alias global
```bash
# Configuration (une fois)
echo 'alias patator="/chemin/vers/Patator/patator"' >> ~/.zshrc
source ~/.zshrc

# Utilisation (depuis n'importe où)
patator
```

---

## 📊 Ce que fait le script en détail

### 1️⃣ Vérification Pré-requis
- Vérifie que Docker est installé
- Vérifie que Python 3 est installé
- Vérifie que curl est installé
- Arrête si un élément manque

### 2️⃣ Infrastructure Docker
```bash
docker compose up -d
```
Lance 13 services :
- postgres (base relationnelle)
- mongodb (base NoSQL)
- kafka-1, kafka-2, kafka-3 (cluster)
- zookeeper (coordination)
- flink-jobmanager, flink-taskmanager
- minio (stockage S3-like)
- kafka-ui, prometheus, grafana
- postgres-exporter

### 3️⃣ Chargement Données
```bash
python3 scripts/load_data_to_postgres.py
python3 scripts/load_events_to_mongodb.py
```
Résultat :
- PostgreSQL : 7 tables (2,500 clients, 100 produits, etc.)
- MongoDB : 71,694 événements comportementaux

### 4️⃣ Configuration Kafka
```bash
python3 scripts/create_kafka_topics.py
python3 scripts/stream_events_to_kafka.py
```
Résultat :
- 4 topics créés (user-events, payments, orders, fraud-alerts)
- 71,694 événements streamés
- Partitionnement par customer_id

### 5️⃣ Détection Fraude
```bash
python3 scripts/fraud_detection_realtime.py
```
Résultat :
- 10,857 alertes détectées
- 11 règles appliquées (basiques + avancées)
- Stockage dans PostgreSQL (table fraud_alerts)
- Publication dans Kafka (topic fraud-alerts)

### 6️⃣ API Backend
```bash
python3 api/fraud_dashboard_api.py &
```
Résultat :
- FastAPI sur http://localhost:8000
- 7 endpoints REST opérationnels
- Synchronisation automatique depuis Kafka

### 7️⃣ Dashboard Web
```bash
cd dashboard && python3 -m http.server 7600 &
```
Résultat :
- Serveur HTTP sur http://localhost:7600
- Interface web analyst accessible
- Auto-refresh toutes les 30s

### 8️⃣ Récapitulatif
Affiche :
- 📊 Statistiques (total alertes, taux de fraude)
- 🌐 URLs d'accès aux services
- 📝 Commandes pour consulter les logs
- 🛑 Commande pour tout arrêter

---

## 🎨 Fonctionnalités du Script

### Gestion Intelligente
- ✅ **Skip si déjà fait** : Ne recharge pas les données si déjà présentes
- ✅ **Retry automatique** : Réessaye en cas d'échec temporaire
- ✅ **Wait for services** : Attend que les services soient prêts
- ✅ **Port conflicts** : Détecte et libère les ports occupés
- ✅ **Logs centralisés** : Tous les logs dans `logs/`

### Affichage Coloré
- 🟢 **Vert** : Succès
- 🔴 **Rouge** : Erreur
- 🟡 **Jaune** : Warning
- 🔵 **Bleu** : Info
- 🟣 **Violet** : Headers

### Ouverture Auto
Le script ouvre automatiquement le dashboard dans le navigateur (macOS/Linux/Windows).

---

## 📁 Structure des Logs

Tous les logs sont dans `logs/` :

```
logs/
├── fraud_dashboard_api.log     # API Backend
├── fraud_detection.log          # Détection de fraude
└── http_server.log              # Serveur web dashboard
```

### Consulter les logs
```bash
# En temps réel
tail -f logs/fraud_dashboard_api.log
tail -f logs/fraud_detection.log

# Dernières lignes
tail -50 logs/fraud_dashboard_api.log

# Recherche dans les logs
grep "ERROR" logs/*.log
```

---

## 🔧 Personnalisation

### Modifier les ports
Éditer les variables dans `patator` :
```bash
API_PORT=8000
DASHBOARD_PORT=7600
```

### Désactiver l'ouverture auto du navigateur
Commenter la ligne dans la fonction `main()` :
```bash
# open_dashboard
```

### Changer le timeout
Modifier dans les fonctions `wait_for_service` :
```bash
local max_attempts=30  # 30 secondes par défaut
```

---

## 🛑 Arrêter les Services

### Arrêt complet
```bash
cd /chemin/vers/Patator
docker compose down
```

### Arrêt + suppression volumes
```bash
docker compose down -v
```

### Arrêt d'un service spécifique
```bash
# API
pkill -f fraud_dashboard_api.py

# Dashboard
pkill -f "http.server 7600"

# Kafka
docker compose stop kafka-1 kafka-2 kafka-3
```

---

## 🐛 Debugging

### Vérifier l'exécution
```bash
# Services Docker
docker compose ps

# API Backend
curl http://localhost:8000/health

# Dashboard
curl -I http://localhost:7600/fraud_dashboard.html

# Kafka topics
docker compose exec kafka-1 kafka-topics --bootstrap-server localhost:9092 --list
```

### Problèmes courants

#### "Port already in use"
```bash
# Libérer le port
lsof -ti:8000 | xargs kill -9
lsof -ti:7600 | xargs kill -9
```

#### "Docker not responding"
```bash
# Redémarrer Docker Desktop
# Ou redémarrer le daemon
sudo systemctl restart docker
```

#### "Kafka topics not created"
```bash
# Créer manuellement
python3 scripts/create_kafka_topics.py
```

#### "No data in PostgreSQL"
```bash
# Recharger
python3 scripts/load_data_to_postgres.py
```

---

## 📊 Résultat Final

Une fois lancé, vous aurez accès à :

### Services Principaux
| Service | URL | Description |
|---------|-----|-------------|
| **Dashboard** | http://localhost:7600/fraud_dashboard.html | Interface analyst |
| **API** | http://localhost:8000 | Backend REST |
| **Kafka UI** | http://localhost:8082 | Monitoring Kafka |
| **Flink UI** | http://localhost:8083 | Monitoring Flink |
| **Grafana** | http://localhost:4000 | Dashboards |
| **Prometheus** | http://localhost:9090 | Métriques |

### Statistiques
- 📊 **10,857 alertes** de fraude détectées
- 🚨 **143.55%** de taux de fraude
- 🔴 **3,463 alertes HIGH** (31.9%)
- 🟠 **7,394 alertes MEDIUM** (68.1%)

---

## 👥 Pour les Autres Utilisateurs

Si quelqu'un clone ton projet :

```bash
# 1. Cloner
git clone https://github.com/ChevalierPierree/ProjetDataM1JeanPierre.git
cd ProjetDataM1JeanPierre
git checkout PierreDump

# 2. Installer dépendances
pip3 install -r requirements.txt

# 3. Lancer
chmod +x patator
./patator

# 4. Profiter !
# Dashboard : http://localhost:7600/fraud_dashboard.html
```

**C'est tout !** 🎉

---

## 💡 Conseils

### Première utilisation
La première fois, le script prend ~5 minutes car il doit :
- Télécharger les images Docker (~2 GB)
- Charger toutes les données
- Streamer 71k événements
- Générer 10k+ alertes

### Utilisations suivantes
Les fois suivantes, le script est beaucoup plus rapide (~1 minute) car :
- Images Docker déjà téléchargées
- Données déjà chargées (skip automatique)
- Kafka topics déjà créés (skip automatique)

### Environnement de développement
Pour développer sans relancer tout :
```bash
# Garder Docker actif
docker compose up -d

# Relancer juste l'API
pkill -f fraud_dashboard_api.py
python3 api/fraud_dashboard_api.py > logs/fraud_dashboard_api.log 2>&1 &

# Relancer juste le dashboard
pkill -f "http.server 7600"
cd dashboard && python3 -m http.server 7600 > ../logs/http_server.log 2>&1 &
```

---

## 🎓 Technologies

Le script utilise :
- **Bash** (scripting)
- **Docker Compose** (orchestration)
- **Python 3** (backend + processing)
- **curl** (healthchecks)
- **lsof** (gestion ports)
- **jq** (parsing JSON - optionnel)

---

## 📝 Maintenance

### Mise à jour du script
```bash
# Rendre exécutable après modification
chmod +x patator

# Tester
./patator
```

### Ajouter une étape
Créer une nouvelle fonction dans `patator` :
```bash
my_custom_step() {
    print_header "X️⃣  MA NOUVELLE ÉTAPE"
    print_step "Exécution de ma tâche"
    # ... votre code ...
    print_success "Tâche terminée"
}

# Ajouter dans main()
main() {
    # ... étapes existantes ...
    my_custom_step
    # ...
}
```

---

## 🏆 Avantages

### Pour Toi
- ✅ **Un seul mot** : tape `patator` et tout démarre
- ✅ **Pas de oubli** : toutes les étapes sont automatisées
- ✅ **Logs propres** : tout centralisé dans `logs/`
- ✅ **Démo rapide** : présentation en 5 minutes chrono

### Pour les Autres
- ✅ **Installation simple** : clone + `./patator`
- ✅ **Reproductible** : fonctionne sur n'importe quelle machine
- ✅ **Documenté** : messages clairs à chaque étape
- ✅ **Professionnel** : script de production-grade

---

## 📖 Documentation Associée

- 📘 `README.md` - Vue d'ensemble projet
- 📗 `INSTALLATION.md` - Guide installation détaillé
- 📙 `QUICKSTART.md` - Démarrage rapide
- 📕 `AUDIT_RENDU_PROJET.md` - Audit de rendu et périmètre
- 📓 `FRAUD_DASHBOARD_README.md` - Guide dashboard

---

**Créé par** : Pierre Chevalier  
**Projet** : M1 Data Engineering - EFREI  
**Date** : Février 2026  
**Version** : 1.0.0
