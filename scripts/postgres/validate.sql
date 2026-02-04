\echo '=== COUNTS ==='
SELECT 'customers' AS table_name, COUNT(*) AS rows FROM customers;
SELECT 'products' AS table_name, COUNT(*) AS rows FROM products;
SELECT 'sessions' AS table_name, COUNT(*) AS rows FROM sessions;
SELECT 'orders' AS table_name, COUNT(*) AS rows FROM orders;
SELECT 'order_items' AS table_name, COUNT(*) AS rows FROM order_items;
SELECT 'payments' AS table_name, COUNT(*) AS rows FROM payments;
SELECT 'fraud_alerts' AS table_name, COUNT(*) AS rows FROM fraud_alerts;

\echo '\n=== REFERENTIAL INTEGRITY ==='
SELECT COUNT(*) AS orphan_orders
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

SELECT COUNT(*) AS orphan_order_items
FROM order_items oi
LEFT JOIN orders o ON oi.order_id = o.order_id
WHERE o.order_id IS NULL;

SELECT COUNT(*) AS orphan_order_items_products
FROM order_items oi
LEFT JOIN products p ON oi.product_id = p.product_id
WHERE p.product_id IS NULL;

SELECT COUNT(*) AS orphan_payments
FROM payments p
LEFT JOIN orders o ON p.order_id = o.order_id
WHERE o.order_id IS NULL;

SELECT COUNT(*) AS orphan_fraud_alerts
FROM fraud_alerts fa
LEFT JOIN payments p ON fa.payment_id = p.payment_id
WHERE p.payment_id IS NULL;

\echo '\n=== BUSINESS METRICS ==='
SELECT
  COUNT(*) FILTER (WHERE status = 'paid') AS paid_orders,
  COUNT(*) FILTER (WHERE status = 'pending') AS pending_orders,
  COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled_orders
FROM orders;

SELECT
  ROUND(AVG(total_amount)::numeric, 2) AS avg_order_value,
  ROUND(SUM(total_amount)::numeric, 2) AS total_revenue
FROM orders
WHERE status = 'paid';

SELECT
  COUNT(*) AS fraud_payments,
  ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM payments), 0), 2) AS fraud_rate_pct
FROM payments
WHERE is_fraudulent = TRUE;

\echo '\n=== TOP CATEGORIES ==='
SELECT
  p.category,
  SUM(oi.quantity) AS total_qty,
  ROUND(SUM(oi.quantity * oi.unit_price)::numeric, 2) AS revenue
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.category
ORDER BY revenue DESC
LIMIT 5;
