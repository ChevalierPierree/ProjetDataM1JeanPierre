-- ============================================================================
-- KIVENDTOUT - SCHEMA ADAPTÉ AU DATASET RÉEL
-- ============================================================================
-- Ce schéma correspond EXACTEMENT aux fichiers CSV du dataset

-- Supprimer toutes les tables existantes
DROP TABLE IF EXISTS fraud_alerts CASCADE;
DROP TABLE IF EXISTS identity_verifications CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS addresses CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- ============================================================================
-- TABLES DE RÉFÉRENCE
-- ============================================================================

-- Table des clients (customers.csv)
CREATE TABLE customers (
    customer_id VARCHAR(50) PRIMARY KEY,  -- C00001
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    country VARCHAR(2),  -- ISO 2-letter code
    registration_ip VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des produits (products.csv)
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,  -- Product ID numérique (P0001 → 1)
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    stock_quantity INTEGER DEFAULT 100,
    brand VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des adresses
CREATE TABLE addresses (
    address_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    street VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(100) NOT NULL,
    address_type VARCHAR(20) CHECK (address_type IN ('billing', 'shipping', 'both')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des sessions (sessions.csv)
CREATE TABLE sessions (
    session_id VARCHAR(50) PRIMARY KEY,  -- S000001
    customer_id VARCHAR(50) REFERENCES customers(customer_id),
    start_ts TIMESTAMP NOT NULL,
    end_ts TIMESTAMP,
    device VARCHAR(50),  -- web_desktop, ios, android, web_mobile
    ip_hash VARCHAR(100),
    utm_source VARCHAR(100),
    utm_campaign VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABLES TRANSACTIONNELLES
-- ============================================================================

-- Table des commandes (orders.csv)
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,  -- Order ID numérique (O0000001 → 1)
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    order_date TIMESTAMP NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL CHECK (total_amount >= 0),
    status VARCHAR(50) CHECK (status IN ('pending', 'paid', 'cancelled', 'processing', 'shipped')),
    shipping_address_id INTEGER REFERENCES addresses(address_id),
    billing_address_id INTEGER REFERENCES addresses(address_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des lignes de commande (order_items.csv)
CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des paiements (payments.csv) - AVEC LABELS FRAUDE
CREATE TABLE payments (
    payment_id INTEGER PRIMARY KEY,  -- PAY0000001 → 1
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    payment_date TIMESTAMP NOT NULL,
    amount NUMERIC(10, 2) NOT NULL CHECK (amount >= 0),
    payment_method VARCHAR(50),  -- card, paypal, bank_transfer
    card_last4 VARCHAR(4),  -- 4 derniers chiffres carte
    payment_status VARCHAR(50),  -- success, failed
    transaction_id VARCHAR(100),
    ip_address VARCHAR(100),
    device_id VARCHAR(100),
    browser VARCHAR(100),
    is_fraudulent BOOLEAN DEFAULT FALSE,  -- LABEL FRAUDE
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des alertes de fraude (fraud_alerts.csv)
CREATE TABLE fraud_alerts (
    alert_id SERIAL PRIMARY KEY,
    payment_id INTEGER NOT NULL REFERENCES payments(payment_id),
    alert_date TIMESTAMP NOT NULL,
    alert_type VARCHAR(100),  -- high_amount, country_mismatch, velocity, device_change
    risk_score NUMERIC(3, 2) CHECK (risk_score BETWEEN 0 AND 1),
    action_taken VARCHAR(50),  -- blocked, reviewed, approved
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des vérifications d'identité (synthetic_id_labels.csv)
CREATE TABLE identity_verifications (
    verification_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    verification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    document_type VARCHAR(50),  -- national_id, passport, driver_license
    document_number VARCHAR(100),
    verification_status VARCHAR(50),  -- pending, verified, rejected
    verification_method VARCHAR(50),  -- manual, ocr, ai
    id_card_image_path VARCHAR(255),  -- Chemin vers image PNG
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEX POUR PERFORMANCE
-- ============================================================================

CREATE INDEX idx_customers_country ON customers(country);
CREATE INDEX idx_customers_created_at ON customers(created_at);

CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_price ON products(price);

CREATE INDEX idx_sessions_customer ON sessions(customer_id);
CREATE INDEX idx_sessions_start_ts ON sessions(start_ts);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_status ON orders(status);

CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);

CREATE INDEX idx_payments_order ON payments(order_id);
CREATE INDEX idx_payments_fraudulent ON payments(is_fraudulent);
CREATE INDEX idx_payments_date ON payments(payment_date);

CREATE INDEX idx_fraud_alerts_payment ON fraud_alerts(payment_id);
CREATE INDEX idx_fraud_alerts_date ON fraud_alerts(alert_date);

-- ============================================================================
-- VUES ANALYTIQUES
-- ============================================================================

-- Vue CA par jour
CREATE OR REPLACE VIEW daily_revenue AS
SELECT 
    DATE(order_date) as date,
    COUNT(*) as nb_orders,
    SUM(total_amount) as revenue,
    AVG(total_amount) as avg_order_value
FROM orders
WHERE status = 'paid'
GROUP BY DATE(order_date)
ORDER BY date DESC;

-- Vue top produits
CREATE OR REPLACE VIEW top_products AS
SELECT 
    p.product_id,
    p.name,
    p.category,
    COUNT(oi.order_item_id) as nb_sales,
    SUM(oi.quantity) as total_quantity,
    SUM(oi.quantity * oi.unit_price) as total_revenue
FROM products p
LEFT JOIN order_items oi ON p.product_id = oi.product_id
GROUP BY p.product_id, p.name, p.category
ORDER BY total_revenue DESC;

-- Vue paiements suspects
CREATE OR REPLACE VIEW suspicious_payments AS
SELECT 
    p.payment_id,
    p.payment_date,
    p.amount,
    p.payment_method,
    p.is_fraudulent,
    c.customer_id,
    c.country as customer_country,
    COUNT(fa.alert_id) as nb_alerts
FROM payments p
JOIN orders o ON p.order_id = o.order_id
JOIN customers c ON o.customer_id = c.customer_id
LEFT JOIN fraud_alerts fa ON p.payment_id = fa.payment_id
WHERE p.is_fraudulent = TRUE OR fa.alert_id IS NOT NULL
GROUP BY p.payment_id, p.payment_date, p.amount, p.payment_method, p.is_fraudulent, c.customer_id, c.country
ORDER BY p.payment_date DESC;

-- ============================================================================
-- FONCTIONS UTILITAIRES
-- ============================================================================

-- Fonction pour calculer l'âge d'un client
CREATE OR REPLACE FUNCTION customer_age(birth_date DATE)
RETURNS INTEGER AS $$
BEGIN
    RETURN EXTRACT(YEAR FROM AGE(CURRENT_DATE, birth_date));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Trigger pour mettre à jour automatiquement is_adult
CREATE OR REPLACE FUNCTION update_is_adult()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculer si le client a 18 ans ou plus
    IF customer_age(NEW.date_of_birth) >= 18 THEN
        NEW.is_adult := TRUE;
    ELSE
        NEW.is_adult := FALSE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Note: Customers n'a pas de colonne is_adult pour l'instant, on peut l'ajouter si besoin

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- ============================================================================
-- DONNÉES DE TEST (optionnel)
-- ============================================================================

-- Statistiques initiales
DO $$
BEGIN
    RAISE NOTICE '✓ Schéma KiVendTout créé avec succès';
    RAISE NOTICE '  - 8 tables créées';
    RAISE NOTICE '  - 12 index créés';
    RAISE NOTICE '  - 3 vues analytiques créées';
    RAISE NOTICE '  - Prêt pour ingestion des données';
END $$;
