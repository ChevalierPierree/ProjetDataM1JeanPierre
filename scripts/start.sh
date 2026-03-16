#!/bin/bash

# ============================================================================
# SCRIPT DE DÉMARRAGE - KIVENDTOUT
# ============================================================================

set -e

echo "🚀 Démarrage de l'infrastructure KiVendTout..."

# Vérifier que Docker est installé
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

# Vérifier que Docker Compose est installé
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

# Créer le fichier .env s'il n'existe pas
if [ ! -f .env ]; then
    echo "📝 Création du fichier .env à partir de .env.example..."
    cp .env.example .env
    echo "✅ Fichier .env créé. Pensez à l'adapter si nécessaire."
fi

# Créer les dossiers de données s'ils n'existent pas
echo "📁 Création des dossiers de données..."
mkdir -p data/raw data/processed data/external
touch data/raw/.gitkeep data/processed/.gitkeep data/external/.gitkeep

# Démarrer les services
echo "🐳 Démarrage des conteneurs Docker..."
docker compose up -d

# Attendre que les services soient prêts
echo "⏳ Attente du démarrage des services..."
sleep 10

# Vérifier le statut
echo ""
echo "📊 Statut des services :"
docker compose ps

echo ""
echo "✅ Infrastructure démarrée avec succès !"
echo ""
echo "🌐 Accès aux services :"
echo "  - PostgreSQL:    localhost:5432 (postgres/postgres)"
echo "  - MongoDB:       localhost:27017 (admin/admin)"
echo "  - MinIO:         http://localhost:9001 (root: MINIO_ROOT_USER/MINIO_ROOT_PASSWORD depuis .env)"
echo "  - Kafka UI:      http://localhost:8080"
echo "  - Prometheus:    http://localhost:9090"
echo "  - Grafana:       http://localhost:3000 (admin/admin)"
echo ""
echo "📚 Consultez le README.md pour plus d'informations."
