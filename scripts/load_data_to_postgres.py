#!/usr/bin/env python3
"""
Script d'ingestion des données KiVendTout dans PostgreSQL
Charge les fichiers CSV du dataset dans la base de données
"""

import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
from pathlib import Path

# Configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'kivendtout',
    'user': 'postgres',
    'password': 'postgres'
}

DATASET_DIR = Path(__file__).parent.parent / 'kivendtout_dataset'

class Colors:
    """Couleurs pour l'affichage terminal"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Affiche un header stylisé"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def print_success(text):
    """Affiche un message de succès"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_warning(text):
    """Affiche un avertissement"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_error(text):
    """Affiche une erreur"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_info(text):
    """Affiche une info"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")

def connect_db():
    """Connexion à PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print_success(f"Connecté à PostgreSQL: {DB_CONFIG['database']}")
        return conn
    except Exception as e:
        print_error(f"Erreur de connexion à PostgreSQL: {e}")
        sys.exit(1)

def load_customers(conn, csv_path):
    """Charge les clients dans PostgreSQL"""
    print_info("Chargement des clients...")
    
    df = pd.read_csv(csv_path)
    print_info(f"  {len(df)} clients trouvés dans le CSV")
    
    cursor = conn.cursor()
    
    # Vider la table d'abord (cascade supprimera les dépendances)
    cursor.execute("TRUNCATE TABLE customers CASCADE;")
    
    # Préparer les données
    insert_query = """
        INSERT INTO customers (email, first_name, last_name, phone, date_of_birth, identity_verified)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    data = []
    for _, row in df.iterrows():
        # Générer email, nom, prénom depuis customer_id
        customer_id = row['customer_id']
        email = f"{customer_id.lower()}@kivendtout.com"
        first_name = f"Client{customer_id[1:]}"
        last_name = f"Test{customer_id[1:]}"
        
        data.append((
            email,
            first_name,
            last_name,
            None,  # phone
            row['birthdate'],
            row['is_minor'] == 0  # identity_verified si adulte
        ))
    
    execute_batch(cursor, insert_query, data, page_size=500)
    conn.commit()
    
    print_success(f"  {len(data)} clients insérés")
    cursor.close()

def load_products(conn, csv_path):
    """Charge les produits dans PostgreSQL"""
    print_info("Chargement des produits...")
    
    df = pd.read_csv(csv_path)
    print_info(f"  {len(df)} produits trouvés dans le CSV")
    
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE products CASCADE;")
    
    insert_query = """
        INSERT INTO products (name, description, category, price, stock_quantity, is_adult_only)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    data = []
    for _, row in df.iterrows():
        data.append((
            row['name'],
            f"Description de {row['name']}",
            row['category'],
            float(row['unit_price']),
            100,  # stock par défaut
            bool(row['is_adult_restricted'])
        ))
    
    execute_batch(cursor, insert_query, data, page_size=500)
    conn.commit()
    
    print_success(f"  {len(data)} produits insérés")
    cursor.close()

def load_orders(conn, csv_path):
    """Charge les commandes dans PostgreSQL"""
    print_info("Chargement des commandes...")
    
    df = pd.read_csv(csv_path)
    print_info(f"  {len(df)} commandes trouvées dans le CSV")
    
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE orders CASCADE;")
    
    # Récupérer les customer_id de la DB
    cursor.execute("SELECT email FROM customers;")
    valid_customers = {row[0] for row in cursor.fetchall()}
    
    insert_query = """
        INSERT INTO orders (customer_id, order_date, status, total_amount)
        VALUES (
            (SELECT customer_id FROM customers WHERE email = %s LIMIT 1),
            %s, %s, %s
        )
    """
    
    data = []
    skipped = 0
    for _, row in df.iterrows():
        customer_email = f"{row['customer_id'].lower()}@kivendtout.com"
        
        if customer_email not in valid_customers:
            skipped += 1
            continue
        
        # Mapper les status
        status_map = {
            'paid': 'delivered',
            'pending': 'pending',
            'cancelled': 'cancelled'
        }
        status = status_map.get(row['status'], 'pending')
        
        data.append((
            customer_email,
            row['order_ts'],
            status,
            float(row['total_amount'])
        ))
    
    execute_batch(cursor, insert_query, data, page_size=500)
    conn.commit()
    
    print_success(f"  {len(data)} commandes insérées")
    if skipped > 0:
        print_warning(f"  {skipped} commandes ignorées (client inexistant)")
    
    cursor.close()

def load_order_items(conn, csv_path):
    """Charge les articles de commande dans PostgreSQL"""
    print_info("Chargement des articles de commande...")
    
    df = pd.read_csv(csv_path)
    print_info(f"  {len(df)} articles trouvés dans le CSV")
    
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE order_items;")
    
    # Récupérer les order_id et product_id valides avec leurs prix
    cursor.execute("SELECT order_id FROM orders;")
    valid_orders = {row[0] for row in cursor.fetchall()}
    
    cursor.execute("SELECT product_id, name, price FROM products;")
    product_map = {}  # product_id -> (internal_id, price)
    for row in cursor.fetchall():
        product_id = row[0]
        name = row[1]
        price = row[2]
        # Mapper à la fois par ID et par nom
        product_map[name] = (product_id, price)
    
    insert_query = """
        INSERT INTO order_items (order_id, product_id, quantity, unit_price)
        VALUES (%s, %s, %s, %s)
    """
    
    data = []
    skipped = 0
    for _, row in df.iterrows():
        # Extraire le numéro de l'order_id (O0000001 -> 1)
        try:
            order_num = int(row['order_id'].replace('O', ''))
            if order_num not in valid_orders:
                skipped += 1
                continue
        except:
            skipped += 1
            continue
        
        # Trouver le product_id et le prix
        product_name = f"Product {row['product_id'].replace('P', '')}"
        product_info = product_map.get(product_name)
        
        if not product_info:
            skipped += 1
            continue
        
        product_id, unit_price = product_info
        
        data.append((
            order_num,
            product_id,
            int(row['qty']),  # Utilise 'qty' au lieu de 'quantity'
            float(unit_price)
        ))
    
    execute_batch(cursor, insert_query, data, page_size=500)
    conn.commit()
    
    print_success(f"  {len(data)} articles insérés")
    if skipped > 0:
        print_warning(f"  {skipped} articles ignorés (références invalides)")
    
    cursor.close()

def load_payments(conn, csv_path):
    """Charge les paiements dans PostgreSQL"""
    print_info("Chargement des paiements...")
    
    df = pd.read_csv(csv_path)
    print_info(f"  {len(df)} paiements trouvés dans le CSV")
    
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE payments CASCADE;")
    
    # Récupérer les order_id valides
    cursor.execute("SELECT order_id FROM orders;")
    valid_orders = {row[0] for row in cursor.fetchall()}
    
    insert_query = """
        INSERT INTO payments (order_id, payment_method, amount, status, transaction_id, is_fraudulent, fraud_score, payment_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    # Créer un mapping payment_id -> order_id
    cursor.execute("SELECT order_id FROM orders ORDER BY order_id;")
    order_ids = [row[0] for row in cursor.fetchall()]
    
    data = []
    skipped = 0
    for idx, row in df.iterrows():
        # Associer un payment à un order (simple mapping séquentiel)
        if idx < len(order_ids):
            order_id = order_ids[idx]
        else:
            skipped += 1
            continue
        
        # Mapper les méthodes de paiement
        method_map = {
            'card': 'credit_card',
            'paypal': 'paypal',
            'bank_transfer': 'bank_transfer'
        }
        method = method_map.get(row['method'], 'credit_card')
        
        # Mapper les statuts
        status = 'completed' if row['result'] == 'success' else 'failed'
        
        # Score de fraude (0-1 -> 0-100)
        fraud_score = 90.0 if row['is_fraud_label'] == 1 else 10.0
        
        data.append((
            order_id,
            method,
            float(row['amount']),
            status,
            row['payment_id'],
            bool(row['is_fraud_label']),
            fraud_score,
            row['attempt_ts']
        ))
    
    execute_batch(cursor, insert_query, data, page_size=500)
    conn.commit()
    
    print_success(f"  {len(data)} paiements insérés")
    if skipped > 0:
        print_warning(f"  {skipped} paiements ignorés")
    
    cursor.close()

def load_fraud_alerts(conn, csv_path):
    """Charge les alertes de fraude dans PostgreSQL"""
    print_info("Chargement des alertes de fraude...")
    
    df = pd.read_csv(csv_path)
    print_info(f"  {len(df)} alertes trouvées dans le CSV")
    
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE fraud_alerts;")
    
    # Récupérer les payment_id valides
    cursor.execute("SELECT payment_id, transaction_id FROM payments;")
    payment_map = {row[1]: row[0] for row in cursor.fetchall()}  # transaction_id -> payment_id
    
    insert_query = """
        INSERT INTO fraud_alerts (payment_id, alert_type, severity, description, status)
        VALUES (%s, %s, %s, %s, %s)
    """
    
    data = []
    skipped = 0
    for _, row in df.iterrows():
        payment_id = payment_map.get(row['payment_id'])
        
        if not payment_id:
            skipped += 1
            continue
        
        # Mapper la sévérité
        severity_map = {
            'high_amount': 'high',
            'country_mismatch': 'medium',
            'velocity': 'high',
            'device_change': 'low'
        }
        severity = severity_map.get(row['rule_triggered'], 'medium')
        
        # Statut
        status = 'resolved' if row['is_fraud_label'] == 1 else 'false_positive'
        
        data.append((
            payment_id,
            row['rule_triggered'],
            severity,
            f"Alerte déclenchée par règle: {row['rule_triggered']}",
            status
        ))
    
    execute_batch(cursor, insert_query, data, page_size=500)
    conn.commit()
    
    print_success(f"  {len(data)} alertes insérées")
    if skipped > 0:
        print_warning(f"  {skipped} alertes ignorées (paiement inexistant)")
    
    cursor.close()

def display_statistics(conn):
    """Affiche les statistiques de la base de données"""
    print_header("STATISTIQUES DE LA BASE DE DONNÉES")
    
    cursor = conn.cursor()
    
    tables = [
        ('customers', 'Clients'),
        ('products', 'Produits'),
        ('orders', 'Commandes'),
        ('order_items', 'Articles commandés'),
        ('payments', 'Paiements'),
        ('fraud_alerts', 'Alertes de fraude')
    ]
    
    for table, label in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchall()[0][0]
        print(f"  {label:.<40} {count:>6} lignes")
    
    # Statistiques supplémentaires
    print(f"\n{Colors.BOLD}Statistiques métier :{Colors.RESET}")
    
    cursor.execute("SELECT COUNT(*) FROM payments WHERE is_fraudulent = true;")
    fraud_count = cursor.fetchall()[0][0]
    print(f"  Paiements frauduleux :{fraud_count:>6}")
    
    cursor.execute("SELECT COUNT(DISTINCT category) FROM products;")
    categories = cursor.fetchall()[0][0]
    print(f"  Catégories de produits :{categories:>6}")
    
    cursor.execute("SELECT AVG(total_amount) FROM orders;")
    avg_amount = cursor.fetchall()[0][0]
    if avg_amount:
        print(f"  Panier moyen :€{avg_amount:>8.2f}")
    
    cursor.close()

def main():
    """Fonction principale"""
    print_header("INGESTION DATASET KIVENDTOUT VERS POSTGRESQL")
    
    start_time = datetime.now()
    
    # Vérifier que le dataset existe
    if not DATASET_DIR.exists():
        print_error(f"Dossier dataset introuvable: {DATASET_DIR}")
        sys.exit(1)
    
    print_info(f"Dossier dataset: {DATASET_DIR}")
    
    # Connexion
    conn = connect_db()
    
    try:
        # Charger les données dans l'ordre (à cause des FK)
        load_customers(conn, DATASET_DIR / 'customers.csv')
        load_products(conn, DATASET_DIR / 'products.csv')
        load_orders(conn, DATASET_DIR / 'orders.csv')
        load_order_items(conn, DATASET_DIR / 'order_items.csv')
        load_payments(conn, DATASET_DIR / 'payments.csv')
        load_fraud_alerts(conn, DATASET_DIR / 'fraud_alerts.csv')
        
        # Afficher les statistiques
        display_statistics(conn)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print_header("INGESTION TERMINÉE AVEC SUCCÈS")
        print_success(f"Temps d'exécution: {elapsed:.2f} secondes")
        print_info("La base de données est prête à être utilisée !")
        
    except Exception as e:
        print_error(f"Erreur lors de l'ingestion: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        conn.close()
        print_info("Connexion fermée")

if __name__ == "__main__":
    main()
