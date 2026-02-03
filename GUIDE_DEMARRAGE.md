# 🚀 GUIDE DE DÉMARRAGE RAPIDE - KIVENDTOUT

## ✅ ÉTAPE 1 : Configuration Git & GitHub (À FAIRE MAINTENANT)

### 1.1 Créer le repository sur GitHub
1. Aller sur : https://github.com/new
2. **Repository name** : `ProjetDataM1JeanPierre` (ou autre nom)
3. **Description** : `Architecture Data Engineering - Projet M1 - Détection fraude, BI temps réel, IA`
4. **Visibilité** : Privé (recommandé) ou Public
5. ⚠️ **NE PAS** cocher "Initialize this repository with a README"
6. Cliquer sur **"Create repository"**

### 1.2 Lier le repository local à GitHub

Ouvrir un terminal dans le dossier `Patator` et exécuter :

```bash
cd "/Users/pierrechevalier/Desktop/PERSO/EFREI/M1 DATA/Patator"

# Vérifier que Git est initialisé
git status

# Ajouter le remote (remplacer par VOTRE URL GitHub)
git remote add origin https://github.com/VOTRE_USERNAME/VOTRE_REPO.git

# Vérifier
git remote -v

# Pousser le code
git push -u origin main
```

### 1.3 Inviter votre binôme

Sur GitHub, dans votre repository :
1. Cliquer sur **Settings** (en haut)
2. Cliquer sur **Collaborators** (menu gauche)
3. Cliquer sur **Add people**
4. Entrer le username GitHub de votre binôme
5. Lui envoyer l'invitation

---

## ✅ ÉTAPE 2 : Votre binôme clone le projet

Votre binôme doit exécuter :

```bash
# Cloner le repository
git clone https://github.com/VOTRE_USERNAME/VOTRE_REPO.git

# Aller dans le dossier
cd VOTRE_REPO

# Créer le fichier .env
cp .env.example .env
```

---

## ✅ ÉTAPE 3 : Démarrer l'infrastructure Docker

### 3.1 Vérifier les prérequis

```bash
docker --version          # Doit afficher version 24+
docker compose version    # Doit afficher version 2.20+
python3 --version         # Doit afficher version 3.10+
```

### 3.2 Démarrer tous les services

**Option A : Avec le script automatique**
```bash
./scripts/start.sh
```

**Option B : Manuellement**
```bash
# Copier .env si pas fait
cp .env.example .env

# Démarrer tous les services
docker compose up -d

# Voir les logs
docker compose logs -f
```

### 3.3 Vérifier que tout fonctionne

```bash
# Voir le statut de tous les conteneurs
docker compose ps

# Tous doivent être "Up" et "healthy"
```

---

## 🌐 ÉTAPE 4 : Accéder aux services

Une fois démarré, ouvrir dans votre navigateur :

| Service | URL | Login | Mot de passe |
|---------|-----|-------|--------------|
| **MinIO Console** | http://localhost:9001 | `minio` | `minio123` |
| **Kafka UI** | http://localhost:8080 | - | - |
| **Grafana** | http://localhost:3000 | `admin` | `admin` |
| **Prometheus** | http://localhost:9090 | - | - |

### Connexion aux bases de données

**PostgreSQL** (avec DBeaver, pgAdmin ou TablePlus) :
- Host: `localhost`
- Port: `5432`
- Database: `kivendtout`
- User: `postgres`
- Password: `postgres`

**MongoDB** (avec MongoDB Compass) :
- Connection string: `mongodb://admin:admin@localhost:27017`

---

## ✅ ÉTAPE 5 : Installer Python et dépendances

```bash
# Créer un environnement virtuel
python3 -m venv venv

# Activer l'environnement
source venv/bin/activate  # macOS/Linux

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🔍 ÉTAPE 6 : Vérifier que PostgreSQL est initialisé

```bash
# Se connecter à PostgreSQL
docker exec -it kivendtout-postgres psql -U postgres -d kivendtout

# Lister les tables
\dt

# Vous devriez voir :
# - customers
# - products
# - orders
# - payments
# - fraud_alerts
# etc.

# Voir les données de test
SELECT * FROM customers;

# Quitter
\q
```

---

## 🛑 ÉTAPE 7 : Arrêter les services

```bash
# Arrêter tous les services
./scripts/stop.sh

# OU manuellement
docker compose down

# Pour supprimer aussi les données (⚠️ perte de données)
docker compose down -v
```

---

## 🔄 WORKFLOW GIT (Collaboration en binôme)

### Avant de commencer à travailler
```bash
# Récupérer les dernières modifications
git pull origin main
```

### Après avoir fait des modifications
```bash
# Voir ce qui a changé
git status

# Ajouter les fichiers modifiés
git add .

# Créer un commit
git commit -m "Description claire de ce que vous avez fait"

# Pousser vers GitHub
git push origin main
```

### Créer une branche pour une fonctionnalité
```bash
# Créer et basculer sur une nouvelle branche
git checkout -b feature/nom-de-la-feature

# Travailler sur la branche...

# Pousser la branche
git push origin feature/nom-de-la-feature

# Créer une Pull Request sur GitHub pour review
```

---

## 📋 PROCHAINES ÉTAPES DU PROJET

### Phase 1 : Infrastructure de base (SEMAINE 1)
- [x] ✅ Structure du projet créée
- [x] ✅ Docker Compose configuré
- [x] ✅ PostgreSQL initialisé
- [ ] 🔄 Tester la connexion à tous les services
- [ ] 🔄 Créer des données de test plus complètes
- [ ] 🔄 Documenter l'architecture (schéma visuel)

### Phase 2 : Pipelines de données (SEMAINE 2-3)
- [ ] 📝 Configurer Kafka topics
- [ ] 📝 Créer producteurs Kafka (événements utilisateurs)
- [ ] 📝 Créer consommateurs Kafka
- [ ] 📝 Configurer Airflow
- [ ] 📝 Créer premier DAG Airflow (ETL PostgreSQL → MinIO)

### Phase 3 : Stream Processing (SEMAINE 4)
- [ ] 📝 Configurer Apache Flink
- [ ] 📝 Implémenter détection de fraude temps réel
- [ ] 📝 Créer alertes automatiques

### Phase 4 : Transformation & DWH (SEMAINE 5)
- [ ] 📝 Installer et configurer dbt
- [ ] 📝 Créer modèles dbt (staging, intermediate, mart)
- [ ] 📝 Implémenter tests de qualité

### Phase 5 : IA & API (SEMAINE 6)
- [ ] 📝 Créer API FastAPI
- [ ] 📝 Entraîner modèle reconnaissance CNI
- [ ] 📝 Intégrer modèle dans API

### Phase 6 : BI & Monitoring (SEMAINE 7)
- [ ] 📝 Configurer Apache Superset
- [ ] 📝 Créer dashboards BI
- [ ] 📝 Configurer dashboards Grafana
- [ ] 📝 Configurer alertes Prometheus

### Phase 7 : Tests & Documentation (SEMAINE 8)
- [ ] 📝 Tests de charge (JMeter)
- [ ] 📝 Tests de failover (HA)
- [ ] 📝 Documentation complète
- [ ] 📝 Préparation présentation

---

## 🆘 TROUBLESHOOTING

### Docker : "Cannot connect to the Docker daemon"
```bash
# Démarrer Docker Desktop
open -a Docker

# Attendre que Docker soit prêt (icône dans la barre de menu)
```

### Port déjà utilisé (ex: 5432)
```bash
# Trouver le processus qui utilise le port
lsof -i :5432

# Tuer le processus
kill -9 PID

# OU changer le port dans docker-compose.yml
```

### Service ne démarre pas (status "unhealthy")
```bash
# Voir les logs du service
docker compose logs nom-du-service

# Redémarrer le service
docker compose restart nom-du-service
```

### Problème de permissions
```bash
# Donner les droits d'exécution aux scripts
chmod +x scripts/*.sh
```

---

## 📚 RESSOURCES UTILES

### Documentations officielles
- PostgreSQL : https://www.postgresql.org/docs/
- MongoDB : https://www.mongodb.com/docs/
- Kafka : https://kafka.apache.org/documentation/
- Docker : https://docs.docker.com/

### Tutoriels
- Git pour débutants : https://www.youtube.com/watch?v=HVsySz-h9r4
- Docker Compose : https://docs.docker.com/compose/gettingstarted/
- PostgreSQL : https://www.postgresqltutorial.com/

---

## ✅ CHECKLIST AVANT DE COMMENCER

- [ ] Docker Desktop installé et démarré
- [ ] Git configuré (nom et email)
- [ ] Repository GitHub créé
- [ ] Binôme ajouté comme collaborateur
- [ ] Code poussé sur GitHub
- [ ] Binôme a cloné le repository
- [ ] Les 2 personnes peuvent démarrer les services Docker
- [ ] Les 2 personnes peuvent accéder aux interfaces web

---

**🎉 Une fois cette checklist complète, vous êtes prêts à développer !**

Pour toute question, consultez le `README.md` ou créez une issue GitHub.

**Dernière mise à jour** : 3 février 2026
