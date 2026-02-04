\set random_order random(1,1289)
\set random_product random(1,200)
\set random_payment random(1,1583)

SELECT total_amount FROM orders WHERE order_id = :random_order;
SELECT price FROM products WHERE product_id = :random_product;
SELECT COUNT(*) FROM order_items WHERE order_id = :random_order;
SELECT amount FROM payments WHERE payment_id = :random_payment;
