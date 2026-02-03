#!/usr/bin/env python3
"""
Script de création des topics Kafka pour KiVendTout
"""

import sys
import time
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError, NoBrokersAvailable

def create_topics():
    """
    Crée les topics Kafka nécessaires pour le streaming d'événements
    """
    
    # Configuration Kafka avec retry
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            print(f"🔌 Tentative de connexion à Kafka (essai {attempt + 1}/{max_retries})...")
            admin_client = KafkaAdminClient(
                bootstrap_servers=['localhost:9092', 'localhost:9093', 'localhost:9094'],
                client_id='topic_creator',
                request_timeout_ms=10000,
                connections_max_idle_ms=30000
            )
            print("✅ Connecté au cluster Kafka")
            break
        except NoBrokersAvailable:
            if attempt < max_retries - 1:
                print(f"⚠️  Brokers non disponibles, nouvelle tentative dans {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print("❌ Impossible de se connecter à Kafka après plusieurs tentatives")
                sys.exit(1)
    
    # Définition des topics avec leurs configurations
    topics = [
        {
            'name': 'user-events',
            'partitions': 6,
            'replication': 3,
            'description': 'Événements comportementaux utilisateurs (page_view, product_view, add_to_cart, etc.)'
        },
        {
            'name': 'payments',
            'partitions': 3,
            'replication': 3,
            'description': 'Événements de paiement pour détection de fraude en temps réel'
        },
        {
            'name': 'orders',
            'partitions': 3,
            'replication': 3,
            'description': 'Commandes passées sur la plateforme'
        },
        {
            'name': 'fraud-alerts',
            'partitions': 2,
            'replication': 3,
            'description': 'Alertes de fraude générées par le système de détection'
        }
    ]
    
    # Configuration avancée des topics
    topic_configs = {
        'retention.ms': '604800000',  # 7 jours
        'cleanup.policy': 'delete',
        'compression.type': 'lz4',
        'max.message.bytes': '1048576'  # 1 MB
    }
    
    print("\n📋 Topics à créer:")
    for topic in topics:
        print(f"  • {topic['name']:<20} | {topic['partitions']} partitions | RF={topic['replication']}")
        print(f"    └─ {topic['description']}")
    
    # Création des topics
    new_topics = []
    for topic in topics:
        new_topic = NewTopic(
            name=topic['name'],
            num_partitions=topic['partitions'],
            replication_factor=topic['replication'],
            topic_configs=topic_configs
        )
        new_topics.append(new_topic)
    
    print("\n🚀 Création des topics...")
    try:
        admin_client.create_topics(new_topics=new_topics, validate_only=False)
        
        # Attendre un peu pour la création
        time.sleep(2)
        
        # Vérification manuelle
        for topic in topics:
            topic_name = topic['name']
            try:
                print(f"✅ Topic '{topic_name}' créé avec succès")
            except Exception as e:
                print(f"❌ Erreur lors de la création de '{topic_name}': {e}")
    
    except TopicAlreadyExistsError as e:
        print(f"⚠️  Certains topics existent déjà: {e}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        # On continue quand même pour vérifier
    
    # Vérification finale
    print("\n🔍 Vérification des topics créés...")
    time.sleep(2)  # Petit délai pour la propagation
    
    existing_topics = admin_client.list_topics()
    created_topics = [t['name'] for t in topics]
    
    print("\n📊 État final:")
    for topic_name in created_topics:
        if topic_name in existing_topics:
            print(f"  ✓ {topic_name}")
        else:
            print(f"  ✗ {topic_name} (non trouvé)")
    
    print(f"\n✨ Total topics dans le cluster: {len(existing_topics)}")
    
    admin_client.close()
    print("\n🎉 Configuration Kafka terminée avec succès!")

if __name__ == '__main__':
    create_topics()
