#!/usr/bin/env python3
"""
Script d'ingestion COMPLET du dataset KiVendTout vers PostgreSQL
Charge TOUTES les tables : customers, products, sessions, orders, order_items, payments, fraud_alerts
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path
import sys
from datetime import datetime

# Configuration PostgreSQL
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'kivendtout',
    'user': 'postgres',
    'password': 'postgres'
}

DATASET_DIR = Path(__file__).parent.parent / 'kivendtout_dataset'

# Couleurs pour output
class Color:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Color.GREEN}✓{Color.END} {msg}")

def print_info(msg):
    print(f"{Color.BLUE}ℹ{Color.END} {msg}")

def print_warning(msg):
    print(f"{Color.YELLOW}⚠{Color.END} {msg}")

def print_error(msg):
    print(f"{Color.RED}✗{Color.END} {msg}")

def get_connection():
    """Connexion PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print_success(f"Connecté à PostgreSQL: {DB_CONFIG['database']}")
        return conn
    except Exception as e:
        print_error(f"Erreur connexion PostgreSQL: {e}")
        sys.exit(1)

# ============================================================================
# FONCTIONS D'INGESTION PAR TABLE
# ============================================================================

def load_customers(conn, csv_path):
    """Charge les clients"""
    print_info("Chargement des clients...")
    
    df = pd.read_csv(csv_path)
    print_info(f"  {len(df)} clients trouvés dans le CSV")
    
    # Vérifier colonnes
    print_info(f"  Colonnes: {list(df.columns)}")
    
    cursor = conn.cursor()
    
    # Nettoyer table
    cursor.execute("TRUNCATE TABLE customers CASCADE;")
    
    # Mapper colonnes CSV → PostgreSQL
    insert_query = """
        INSERT INTO customers (
            customer_id, email, first_name, last_name, phone,
            date_of_birth, country, registration_ip, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    data = []
    for idx, row in df.iterrows():
        # Générer données manquantes depuis customer_id
        customer_num = int(row['customer_id'].replace('C', ''))
        
        data.append((
            row['customer_id'],
            f"customer{customer_num}@kivendtout.com",  # email généré
            f"FirstName{customer_num}",  # first_name généré
            f"LastName{customer_num}",   # last_name généré
            f"+33612345{customer_num:03d}",  # phone généré
            pd.to_datetime(row['birthdate']),
            row['country'],
            f"192.168.{customer_num % 256}.{customer_num % 256}",  # IP généré
            pd.to_datetime(row['signup_ts'])
        ))
    
    execute_batch(cursor, insert_query, data, page_size=500)
    conn.commit()
    
    print_success(f"  {len(data)} clients insérés")
    cursor.close()

def load_products(conn, csv_path):
    """Charge les produits"""
    print_info("Chargement des produits...")
    
    df = pd.read_csv(csv_path)
    print_info(f"  {len(df)} produits trouvés dans le CSV")
    print_info(f"  Colonnes: {list(df.columns)}")
    
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE products CASCADE;")
    
    insert_query = """
        INSERT INTO products (
            product_id, name, category, subcategory, price,
            stock_quantity, brand, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    data = []
    for _, row in df.iterrows():
        data.append((
            int(row['product_id'].replace('P', '')),
            row['name'],
            row['category'],
            row['category'],  # subcategory = category (pas de colonne dédiée)
            float(row['unit_price']),
            100,  # stock_quantity par défaut
            f"Brand {row['category']}",  # brand généré
            pd.to_datetime(row['created_at'])
        ))
    
    execute_batch(cursor, insert_query, data, page_size=500)
    conn.commit()
    
    print_success(f"  {len(data)} produits insérés")
    cursor.close()

def load_sessions(conn, csv_path):
    """Charge les sessions web - NOUVEAU"""
    print_info("Chargement des sessions...")
    
    df = pd.read_csv(csv_path)
    print_info(f"  {len(df)} sessions trouvées dans le CSV")
    print_info(f"  Colonnes: {list(df.columns)}")
    
    cursor = conn.cursor()
    
    # Créer table sessions si n'existe pas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id VARCHAR(50) PRIMARY KEY,
            customer_id VARCHAR(50) REFERENCES customers(customer_id),
            start_ts TIMESTAMP NOT NULL,
            end_ts TIMESTAMP,
            device VARCHAR(50),
            ip_hash VARCHAR(100),
            utm_source VARCHAR(100),
            utm_campaign VARCHAR(100),
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    cursor.execute("TRUNCATE TABLE sessions CASCADE;")
    
    insert_query = """
        INSERT INTO sessions (
            session_id, customer_id, start_ts, end_ts,
            device, ip_hash, utm_source, utm_campaign, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    # Récupérer customer_ids valides
    cursor.execute("SELECT customer_id FROM customers;")
    valid_customers = {row[0] for row in cursor.fetchall()}
    
    data = []
    skipped = 0
    for _, row in df.iterrows():
        customer_id = row['customer_id']
        
        # Vérifier si customer existe
        if customer_id not in valid_customers:
            skipped += 1
            continue
        
        data.append((
            row['session_id'],
            customer_id,
            pd.to_datetime(row['start_ts']),
            pd.to_datetime(row['end_ts']) if pd.notna(row['end_ts']) else None,
            row['device'],
            row['ip_hash'],
            row['utm_source'],
            row['utm_campaign'],
            pd.to_datetime(row['start_ts'])  # created_at = start_ts
        ))
    
    execute_batch(cursor, insert_query, data, page_size=500)
    conn.commit()
    
    print_success(f"  {len(data)} sessions insérées")
    if skipped > 0:
        print_warning(f"  {skipped} sessions ignorées (customer_id invalide)")
    
    cursor.close()

def load_orders(conn, csv_path):
    """Charge les commandes"""
    print_info("Chargement des commandes...")
    
    df = pd.read_csv(csv_path)
    print_info(f"  {len(df)} commandes trouvées dans le CSV")
    print_info(f"  Colonnes: {list(df.columns)}")
    
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE orders CASCADE;")
    
    # Récupérer customer_ids valides
    cursor.execute("SELECT customer_id FROM customers;")
    valid_customers = {row[0] for row in cursor.fetchall()}
    
    # Créer adresses fictives pour chaque customer
    cursor.execute("""
        INSERT INTO addresses (customer_id, street, city, postal_code, country, address_type, created_at)
        SELECT 
            customer_id,
            '123 Rue de la Paix',
            'Paris',
            '75001',
            country,
            'both',
            created_at
        FROM customers
        ON CONFLICT DO NOTHING;
    """)
    conn.commit()
    
    # Récupérer address_ids par customer
    cursor.execute("SELECT customer_id, address_id FROM addresses;")
    customer_addresses = {row[0]: row[1] for row in cursor.fetchall()}
    
    insert_query = """
        INSERT INTO orders (
            order_id, customer_id, order_date, total_amount, status,
            shipping_address_id, billing_address_id, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    data = []
    skipped = 0
    for _, row in df.iterrows():
        customer_id = row['customer_id']
        
        if customer_id not in valid_customers:
            skipped += 1
            continue
        
        address_id = customer_addresses.get(customer_id)
        if not address_id:
            skipped += 1
            continue
        
        order_num = int(row['order_id'].replace('O', ''))
        
        data.append((
            order_num,
            customer_id,
            pd.to_datetime(row['order_ts']),
            float(row['total_amount']),
            row['status'],
            address_id,
            address_id,
            pd.to_datetime(row['order_ts'])
        ))
    
    execute_batch(cursor, insert_query, data, page_size=500)
    conn.commit()
    
    print_success(f"  {len(data)} commandes insérées")
    if skipped > 0:
        print_warning(f"  {skipped} commandes ignorées (références invalides)")
    
    cursor.close()

def load_order_items(conn, csv_path):
    """Charge les lignes de commande"""
    print_info("Chargement des articles de commande...")
    
    df = pd.read_csv(csv_path)
    print_info(f"  {len(df)} articles trouvés dans le CSV")
    print_info(f"  Colonnes: {list(df.columns)}")
    
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE order_items;")
    
    # Récupérer order_ids valides
    cursor.execute("SELECT order_id FROM orders;")
    valid_orders = {row[0] for row in cursor.fetchall()}
    
    # Récupérer products avec prix
    cursor.execute("SELECT product_id, price FROM products;")
    product_prices = {row[0]: row[1] for row in cursor.fetchall()}
    
    insert_query = """
        INSERT INTO order_items (order_id, product_id, quantity, unit_price, created_at)
        VALUES (%s, %s, %s, %s, %s)
    """
    
    data = []
    skipped = 0
    for _, row in df.iterrows():
        order_num = int(row['order_id'].replace('O', ''))
        product_num = int(row['product_id'].replace('P', ''))
        
        if order_num not in valid_orders:
            skipped += 1
            continue
        
        if product_num not in product_prices:
            skipped += 1
            continue
        
        unit_price = product_prices[product_num]
        
        data.append((
            order_num,
            product_num,
            int(row['qty']),
            float(unit_price),
            datetime.now()
        ))
    
    execute_batch(cursor, insert_query, data, page_size=500)
    conn.commit()
    
    print_success(f"  {len(data)} articles insérés")
    if skipped > 0:
        print_warning(f"  {skipped} articles ignorés (références invalides)")
    
    cursor.close()

def load_payments(conn, csv_path):
    """Charge les paiements avec labels de fraude - NOUVEAU"""
    print_info("Chargement des paiements...")
    
    df = pd.read_csv(csv_path)
    print_info(f"  {len(df)} paiements trouvés dans le CSV")
    print_info(f"  Colonnes: {list(df.columns)}")
    
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE payments CASCADE;")
    
    # Récupérer order_ids valides
    cursor.execute("SELECT order_id FROM orders;")
    valid_orders = {row[0] for row in cursor.fetchall()}
    
    insert_query = """
        INSERT INTO payments (
            payment_id, order_id, payment_date, amount, payment_method,
            card_last4, payment_status, transaction_id, ip_address,
            device_id, browser, is_fraudulent, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    data = []
    fraud_count = 0
    skipped = 0
    
    for idx, row in df.iterrows():
        payment_num = int(row['payment_id'].replace('PAY', ''))
        
        # Trouver order_id correspondant (heuristique: même numéro ou proche)
        order_id = payment_num if payment_num in valid_orders else None
        
        if not order_id:
            # Chercher order proche
            for oid in valid_orders:
                if abs(oid - payment_num) < 5:
                    order_id = oid
                    break
        
        if not order_id:
            skipped += 1
            continue
        
        is_fraud = bool(int(row['is_fraud_label']))  # Convert to boolean
        if is_fraud:
            fraud_count += 1
        
        # Extraire card_last4 depuis card_bin
        card_last4 = str(row['card_bin'])[-4:] if pd.notna(row['card_bin']) else None
        
        data.append((
            payment_num,
            order_id,
            pd.to_datetime(row['attempt_ts']),
            float(row['amount']),
            row['method'],
            card_last4,
            row['result'],  # payment_status
            row['payment_id'],  # transaction_id = payment_id
            row['ip_hash'],  # ip_address
            row['device_id'],
            row['payment_country'],  # browser = country (approximation)
            is_fraud,
            pd.to_datetime(row['attempt_ts'])
        ))
    
    execute_batch(cursor, insert_query, data, page_size=500)
    conn.commit()
    
    print_success(f"  {len(data)} paiements insérés")
    print_info(f"  💰 Paiements frauduleux: {fraud_count} ({fraud_count/len(data)*100:.1f}%)")
    if skipped > 0:
        print_warning(f"  {skipped} paiements ignorés (order_id non trouvé)")
    
    cursor.close()

def load_fraud_alerts(conn, csv_path):
    """Charge les alertes de fraude - NOUVEAU"""
    print_info("Chargement des alertes de fraude...")
    
    df = pd.read_csv(csv_path)
    print_info(f"  {len(df)} alertes trouvées dans le CSV")
    print_info(f"  Colonnes: {list(df.columns)}")
    
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE fraud_alerts;")
    
    # Récupérer payment_ids valides
    cursor.execute("SELECT payment_id FROM payments;")
    valid_payments = {row[0] for row in cursor.fetchall()}
    
    insert_query = """
        INSERT INTO fraud_alerts (
            payment_id, alert_date, alert_type, risk_score,
            action_taken, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    data = []
    skipped = 0
    
    for _, row in df.iterrows():
        payment_num = int(row['payment_id'].replace('PAY', ''))
        
        if payment_num not in valid_payments:
            skipped += 1
            continue
        
        # Mapper rule_triggered vers alert_type et risk_score
        rule = row['rule_triggered']
        risk_scores = {
            'high_amount': 0.85,
            'country_mismatch': 0.75,
            'velocity': 0.90,
            'device_change': 0.70
        }
        risk_score = risk_scores.get(rule, 0.80)
        
        data.append((
            payment_num,
            pd.to_datetime(row['alert_ts']),
            rule,
            risk_score,
            'blocked' if row['is_fraud_label'] else 'reviewed',
            pd.to_datetime(row['alert_ts'])
        ))
    
    execute_batch(cursor, insert_query, data, page_size=500)
    conn.commit()
    
    print_success(f"  {len(data)} alertes insérées")
    if skipped > 0:
        print_warning(f"  {skipped} alertes ignorées (payment_id invalide)")
    
    cursor.close()

# ============================================================================
# VALIDATION ET STATISTIQUES
# ============================================================================

def validate_data(conn):
    """Valide l'intégrité des données"""
    print_info("\n" + "="*60)
    print_info("VALIDATION DE L'INTÉGRITÉ DES DONNÉES")
    print_info("="*60 + "\n")
    
    cursor = conn.cursor()
    
    # 1. Comptage par table
    print_info("📊 Comptage des enregistrements:")
    tables = [
        ('customers', 'Clients'),
        ('products', 'Produits'),
        ('sessions', 'Sessions'),
        ('orders', 'Commandes'),
        ('order_items', 'Lignes de commande'),
        ('payments', 'Paiements'),
        ('fraud_alerts', 'Alertes fraude'),
        ('addresses', 'Adresses')
    ]
    
    for table, label in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchone()[0]
        print_info(f"  {label:.<30} {count:>6,} rows")
    
    # 2. Intégrité référentielle
    print_info("\n🔗 Intégrité référentielle:")
    
    cursor.execute("""
        SELECT COUNT(*) FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.customer_id
        WHERE c.customer_id IS NULL;
    """)
    orphan_orders = cursor.fetchone()[0]
    if orphan_orders == 0:
        print_success("  Commandes → Clients: OK")
    else:
        print_warning(f"  {orphan_orders} commandes orphelines")
    
    cursor.execute("""
        SELECT COUNT(*) FROM order_items oi
        LEFT JOIN products p ON oi.product_id = p.product_id
        WHERE p.product_id IS NULL;
    """)
    orphan_items = cursor.fetchone()[0]
    if orphan_items == 0:
        print_success("  Articles → Produits: OK")
    else:
        print_warning(f"  {orphan_items} articles orphelins")
    
    cursor.execute("""
        SELECT COUNT(*) FROM payments p
        LEFT JOIN orders o ON p.order_id = o.order_id
        WHERE o.order_id IS NULL;
    """)
    orphan_payments = cursor.fetchone()[0]
    if orphan_payments == 0:
        print_success("  Paiements → Commandes: OK")
    else:
        print_warning(f"  {orphan_payments} paiements orphelins")
    
    # 3. Statistiques business
    print_info("\n💰 Statistiques business:")
    
    cursor.execute("SELECT SUM(total_amount) FROM orders WHERE status = 'paid';")
    total_revenue = cursor.fetchone()[0] or 0
    print_info(f"  CA total (commandes payées): {total_revenue:,.2f} €")
    
    cursor.execute("SELECT AVG(total_amount) FROM orders;")
    avg_order = cursor.fetchone()[0] or 0
    print_info(f"  Panier moyen: {avg_order:.2f} €")
    
    cursor.execute("SELECT COUNT(*) FROM payments WHERE is_fraudulent = true;")
    fraud_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM payments;")
    total_payments = cursor.fetchone()[0]
    fraud_rate = (fraud_count / total_payments * 100) if total_payments > 0 else 0
    print_info(f"  Paiements frauduleux: {fraud_count} / {total_payments} ({fraud_rate:.2f}%)")
    
    cursor.execute("""
        SELECT SUM(quantity * unit_price) 
        FROM order_items;
    """)
    total_items_value = cursor.fetchone()[0] or 0
    print_info(f"  Valeur totale articles: {total_items_value:,.2f} €")
    
    cursor.execute("""
        SELECT AVG(item_count) FROM (
            SELECT order_id, COUNT(*) as item_count
            FROM order_items
            GROUP BY order_id
        ) subq;
    """)
    avg_items = cursor.fetchone()[0] or 0
    print_info(f"  Articles moyens par commande: {avg_items:.2f}")
    
    # 4. Top catégories
    print_info("\n🏆 Top 5 catégories vendues:")
    cursor.execute("""
        SELECT p.category, COUNT(*) as nb_ventes, SUM(oi.quantity * oi.unit_price) as ca
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        GROUP BY p.category
        ORDER BY ca DESC
        LIMIT 5;
    """)
    for idx, (category, nb_ventes, ca) in enumerate(cursor.fetchall(), 1):
        print_info(f"  {idx}. {category:.<20} {nb_ventes:>4} ventes | {ca:>10,.2f} €")
    
    cursor.close()

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Orchestration complète de l'ingestion"""
    print("\n" + "="*70)
    print(f"{Color.BOLD}      INGESTION DATASET KIVENDTOUT VERS POSTGRESQL{Color.END}")
    print("="*70 + "\n")
    
    print_info(f"Dossier dataset: {DATASET_DIR}")
    
    start_time = datetime.now()
    
    try:
        # Connexion
        conn = get_connection()
        
        # Ingestion dans l'ordre des dépendances
        print("\n" + "-"*70)
        print(f"{Color.BOLD}PHASE 1 : Tables de référence{Color.END}")
        print("-"*70)
        
        load_customers(conn, DATASET_DIR / 'customers.csv')
        load_products(conn, DATASET_DIR / 'products.csv')
        load_sessions(conn, DATASET_DIR / 'sessions.csv')
        
        print("\n" + "-"*70)
        print(f"{Color.BOLD}PHASE 2 : Tables transactionnelles{Color.END}")
        print("-"*70)
        
        load_orders(conn, DATASET_DIR / 'orders.csv')
        load_order_items(conn, DATASET_DIR / 'order_items.csv')
        load_payments(conn, DATASET_DIR / 'payments.csv')
        load_fraud_alerts(conn, DATASET_DIR / 'fraud_alerts.csv')
        
        # Validation
        validate_data(conn)
        
        # Fermeture
        conn.close()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "="*70)
        print(f"{Color.GREEN}{Color.BOLD}✓ INGESTION TERMINÉE AVEC SUCCÈS{Color.END}")
        print("="*70)
        print_info(f"Durée totale: {duration:.2f} secondes")
        print_info(f"Fin: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print_error(f"\nERREUR CRITIQUE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
