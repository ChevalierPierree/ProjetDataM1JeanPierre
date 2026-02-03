#!/usr/bin/env python3
"""
Producer Kafka - Streaming des événements KiVendTout vers Kafka
Simule un flux d'événements en temps réel
"""

import json
import time
import sys
from datetime import datetime
from pathlib import Path
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

def create_producer(max_retries=5):
    """
    Crée un producer Kafka avec retry et configuration optimale
    """
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            print(f"🔌 Connexion au cluster Kafka (essai {attempt + 1}/{max_retries})...")
            producer = KafkaProducer(
                bootstrap_servers=['localhost:9092', 'localhost:9093', 'localhost:9094'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                compression_type='lz4',
                acks='all',  # Attendre confirmation de tous les réplicas
                retries=3,
                max_in_flight_requests_per_connection=5,
                linger_ms=10,  # Batch pendant 10ms max
                batch_size=16384,  # 16KB par batch
            )
            print("✅ Producer Kafka initialisé")
            return producer
        except NoBrokersAvailable:
            if attempt < max_retries - 1:
                print(f"⚠️  Brokers non disponibles, nouvelle tentative dans {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print("❌ Impossible de se connecter à Kafka")
                sys.exit(1)

def determine_topic(event_type):
    """
    Détermine le topic Kafka en fonction du type d'événement
    """
    payment_events = ['payment_attempt', 'payment_success', 'payment_failure']
    order_events = ['checkout', 'order_completed']
    
    if event_type in payment_events:
        return 'payments'
    elif event_type in order_events:
        return 'orders'
    else:
        return 'user-events'

def stream_events(file_path, speed_multiplier=100, max_events=None):
    """
    Stream les événements vers Kafka
    
    Args:
        file_path: Chemin vers le fichier events.jsonl
        speed_multiplier: Facteur d'accélération (100 = 100x plus rapide)
        max_events: Nombre max d'événements (None = tous)
    """
    producer = create_producer()
    
    print(f"\n📂 Chargement des événements depuis: {file_path}")
    
    # Lecture des événements
    events = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    
    # Tri par timestamp pour respecter l'ordre chronologique
    events.sort(key=lambda x: x['ts'])
    
    if max_events:
        events = events[:max_events]
    
    print(f"📊 {len(events)} événements à streamer")
    print(f"⚡ Vitesse: {speed_multiplier}x plus rapide que le temps réel")
    print(f"📅 Période: {events[0]['ts']} → {events[-1]['ts']}")
    
    # Statistiques par topic
    topic_counts = {'user-events': 0, 'payments': 0, 'orders': 0}
    
    print("\n🚀 Démarrage du streaming...\n")
    
    start_time = time.time()
    sent_count = 0
    last_ts = None
    
    try:
        for i, event in enumerate(events):
            # Déterminer le topic
            topic = determine_topic(event['event_type'])
            
            # Clé de partitionnement (customer_id pour garantir l'ordre par client)
            key = event.get('customer_id', 'anonymous')
            
            # Ajouter des métadonnées
            enriched_event = {
                **event,
                'kafka_ts': datetime.now().isoformat(),
                'stream_sequence': i + 1
            }
            
            # Envoi vers Kafka
            future = producer.send(
                topic=topic,
                key=key,
                value=enriched_event
            )
            
            # Callback optionnel pour debug
            # future.add_callback(lambda metadata: print(f"Envoyé vers {metadata.topic}:{metadata.partition}"))
            
            sent_count += 1
            topic_counts[topic] += 1
            
            # Simulation du délai entre événements (accéléré)
            if last_ts and speed_multiplier > 0:
                current_ts = datetime.fromisoformat(event['ts'])
                previous_ts = datetime.fromisoformat(last_ts)
                real_delay = (current_ts - previous_ts).total_seconds()
                simulated_delay = real_delay / speed_multiplier
                
                if simulated_delay > 0:
                    time.sleep(simulated_delay)
            
            last_ts = event['ts']
            
            # Affichage progressif
            if (i + 1) % 5000 == 0:
                elapsed = time.time() - start_time
                rate = sent_count / elapsed if elapsed > 0 else 0
                print(f"📤 {sent_count:,} événements envoyés | {rate:.0f} evt/s | "
                      f"user-events: {topic_counts['user-events']:,} | "
                      f"payments: {topic_counts['payments']:,} | "
                      f"orders: {topic_counts['orders']:,}")
        
        # Flush final pour garantir l'envoi de tous les messages
        print("\n⏳ Flush des messages restants...")
        producer.flush()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        sys.exit(1)
    finally:
        producer.close()
    
    # Statistiques finales
    elapsed = time.time() - start_time
    print(f"\n{'='*70}")
    print(f"✨ Streaming terminé!")
    print(f"{'='*70}")
    print(f"📊 Événements envoyés: {sent_count:,}")
    print(f"⏱️  Durée totale: {elapsed:.2f}s")
    print(f"⚡ Débit moyen: {sent_count/elapsed:.0f} événements/seconde")
    print(f"\n📨 Distribution par topic:")
    for topic, count in topic_counts.items():
        percentage = (count / sent_count * 100) if sent_count > 0 else 0
        print(f"  • {topic:<15} : {count:>6,} événements ({percentage:>5.1f}%)")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    # Configuration
    dataset_path = Path(__file__).parent.parent / 'kivendtout_dataset' / 'events.jsonl'
    
    if not dataset_path.exists():
        print(f"❌ Fichier non trouvé: {dataset_path}")
        sys.exit(1)
    
    # Options de streaming
    SPEED_MULTIPLIER = 0  # 0 = pas de délai, streaming le plus rapide possible
    MAX_EVENTS = None  # None = tous les événements, ou un nombre pour limiter
    
    print("="*70)
    print("🎬 KAFKA EVENT STREAMING - KiVendTout")
    print("="*70)
    
    stream_events(
        file_path=dataset_path,
        speed_multiplier=SPEED_MULTIPLIER,
        max_events=MAX_EVENTS
    )
