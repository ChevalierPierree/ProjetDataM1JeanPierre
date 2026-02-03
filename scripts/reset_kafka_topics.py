#!/usr/bin/env python3
"""
Script de suppression et recréation des topics Kafka
"""

import sys
import time
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import UnknownTopicOrPartitionError, NoBrokersAvailable

def reset_kafka_topics():
    """
    Supprime tous les topics existants et les recrée propres
    """
    
    # Connexion à Kafka
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            print(f"🔌 Connexion à Kafka (essai {attempt + 1}/{max_retries})...")
            admin_client = KafkaAdminClient(
                bootstrap_servers=['localhost:9092', 'localhost:9093', 'localhost:9094'],
                client_id='topic_resetter',
                request_timeout_ms=10000,
            )
            print("✅ Connecté au cluster Kafka\n")
            break
        except NoBrokersAvailable:
            if attempt < max_retries - 1:
                print(f"⚠️  Brokers non disponibles, nouvelle tentative dans {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print("❌ Impossible de se connecter à Kafka")
                sys.exit(1)
    
    # Liste des topics à supprimer
    topics_to_delete = ['user-events', 'payments', 'orders', 'fraud-alerts']
    
    # Suppression des topics existants
    print("🗑️  Suppression des topics existants...")
    try:
        existing_topics = admin_client.list_topics()
        topics_to_remove = [t for t in topics_to_delete if t in existing_topics]
        
        if topics_to_remove:
            admin_client.delete_topics(topics_to_remove, timeout_ms=5000)
            print(f"✅ {len(topics_to_remove)} topics supprimés: {', '.join(topics_to_remove)}")
            print("⏳ Attente propagation (5 secondes)...")
            time.sleep(5)
        else:
            print("⚠️  Aucun topic à supprimer")
    except UnknownTopicOrPartitionError:
        print("⚠️  Topics déjà supprimés")
    except Exception as e:
        print(f"⚠️  Erreur lors de la suppression: {e}")
    
    # Définition des nouveaux topics
    topics = [
        {
            'name': 'user-events',
            'partitions': 6,
            'replication': 3,
        },
        {
            'name': 'payments',
            'partitions': 3,
            'replication': 3,
        },
        {
            'name': 'orders',
            'partitions': 3,
            'replication': 3,
        },
        {
            'name': 'fraud-alerts',
            'partitions': 2,
            'replication': 3,
        }
    ]
    
    # Configuration des topics
    topic_configs = {
        'retention.ms': '604800000',  # 7 jours
        'cleanup.policy': 'delete',
        'compression.type': 'lz4',
        'max.message.bytes': '1048576'  # 1 MB
    }
    
    # Création des nouveaux topics
    print(f"\n🚀 Création de {len(topics)} topics propres...")
    new_topics = []
    for topic in topics:
        new_topic = NewTopic(
            name=topic['name'],
            num_partitions=topic['partitions'],
            replication_factor=topic['replication'],
            topic_configs=topic_configs
        )
        new_topics.append(new_topic)
        print(f"  • {topic['name']:<20} | {topic['partitions']} partitions | RF={topic['replication']}")
    
    try:
        admin_client.create_topics(new_topics=new_topics, validate_only=False)
        time.sleep(2)
        print("\n✅ Topics créés avec succès")
    except Exception as e:
        print(f"⚠️  Erreur: {e}")
    
    # Vérification finale
    print("\n🔍 Vérification...")
    time.sleep(1)
    existing_topics = admin_client.list_topics()
    
    print("\n📊 État final:")
    for topic in topics:
        status = "✓" if topic['name'] in existing_topics else "✗"
        print(f"  {status} {topic['name']}")
    
    admin_client.close()
    print("\n🎉 Reset Kafka terminé avec succès!\n")
    print("➡️  Vous pouvez maintenant streamer les 71,694 événements propres")

if __name__ == '__main__':
    print("="*70)
    print("🔄 RESET KAFKA TOPICS - Suppression & Recréation")
    print("="*70)
    print("\n⚠️  Cette opération va:")
    print("   1. Supprimer TOUS les messages existants dans Kafka")
    print("   2. Recréer les topics propres")
    print("   3. Vous permettre de streamer uniquement les 71,694 événements\n")
    
    response = input("Continuer ? (oui/non): ")
    if response.lower() in ['oui', 'o', 'yes', 'y']:
        reset_kafka_topics()
    else:
        print("❌ Opération annulée")
