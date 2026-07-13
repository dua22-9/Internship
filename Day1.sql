CREATE DATABASE Day1;
use Day1;
CREATE TABLE customers (
    customer_id INT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    address VARCHAR(255)
);

CREATE TABLE products (
    product_id INT PRIMARY KEY,
    name VARCHAR(100),
    category VARCHAR(50),
    price INT
);

CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    order_date DATE,
    status VARCHAR(20)
);

CREATE TABLE payments (
    payment_id INT PRIMARY KEY,
    order_id INT REFERENCES orders(order_id),
    amount INT,
    payment_date DATE,
    method VARCHAR(20)
);

INSERT INTO customers VALUES 
(1, 'Ali Khan', 'ali@example.com', 'Lahore'),
(2, 'Sara Malik', 'sara@example.com', 'Karachi'),
(3, 'Ahmed Raza', 'ahmed@example.com', 'Islamabad');

INSERT INTO products VALUES 
(1, 'Laptop', 'Electronics', 80000),
(2, 'Phone', 'Electronics', 50000),
(3, 'Shoes', 'Fashion', 6000),
(4, 'Book', 'Stationery', 1200);

INSERT INTO orders VALUES 
(1, 1, '2026-07-01', 'shipped'),
(2, 2, '2026-07-02', 'pending'),
(3, 1, '2026-07-03', 'shipped'),
(4, 3, '2026-07-04', 'cancelled');

INSERT INTO payments VALUES 
(1, 1, 80000, '2026-07-02', 'Credit Card'),
(2, 2, 50000, '2026-07-03', 'Cash'),
(3, 3, 6000, '2026-07-04', 'Debit Card'),
(4, 4, 1200, '2026-07-05', 'Cash');

SELECT c.name, o.order_id, o.order_date
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id;

WITH spending AS (
    SELECT o.customer_id, SUM(p.amount) AS total_spent
    FROM orders o
    JOIN payments p ON o.order_id = p.order_id
    GROUP BY o.customer_id
)
SELECT * FROM spending;

SELECT order_id, payment_date, amount,
       SUM(amount) OVER (PARTITION BY order_id ORDER BY payment_date) AS running_total
FROM payments;

SELECT order_id,
       CASE 
         WHEN status = 'shipped' THEN 'Completed'
         WHEN status = 'pending' THEN 'In Progress'
         ELSE 'Other'
       END AS order_stage
FROM orders;

SELECT customer_id, order_id, order_date,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) AS row_num
FROM orders;

SELECT o.customer_id, SUM(p.amount) AS total_spent,
       RANK() OVER (ORDER BY SUM(p.amount) DESC) AS rank_spending
FROM orders o
JOIN payments p ON o.order_id = p.order_id
GROUP BY o.customer_id;

SELECT product_id, name, price,
       DENSE_RANK() OVER (ORDER BY price DESC) AS price_rank
FROM products;

SELECT order_id, payment_date,
       LEAD(payment_date) OVER (PARTITION BY order_id ORDER BY payment_date) AS next_payment
FROM payments;

SELECT order_id, payment_date, amount,
       LAG(amount) OVER (PARTITION BY order_id ORDER BY payment_date) AS prev_amount
FROM payments;

SELECT *
FROM (
    SELECT o.customer_id, SUM(p.amount) AS total_spent,
           RANK() OVER (ORDER BY SUM(p.amount) DESC) AS rank_spending
    FROM orders o
    JOIN payments p ON o.order_id = p.order_id
    GROUP BY o.customer_id
) ranked
WHERE rank_spending <= 3;

SHOW VARIABLES LIKE 'secure_file_priv';
SHOW VARIABLES LIKE 'local_infile';
SET GLOBAL local_infile = 1;
SHOW TABLES;

-- practicing queries on imported data
SELECT * FROM new_payments;
SELECT * FROM orders_new;
SELECT * FROM new_customers;
SELECT * FROM new_products;

SELECT c.name__firstname, c.name__lastname, p.amount, p.method, p.status
FROM new_customers c
JOIN new_payments p ON c.id = p.customer_id;


WITH customer_payments AS (
    SELECT customer_id, SUM(amount) AS total_paid
    FROM new_payments
    GROUP BY customer_id
)
SELECT c.name__firstname, c.name__lastname, cp.total_paid
FROM new_customers c
JOIN customer_payments cp ON c.id = cp.customer_id;

SELECT customer_id, amount,
       SUM(amount) OVER (PARTITION BY customer_id ORDER BY payment_id) AS running_total
FROM new_payments;

SELECT payment_id, amount,
       CASE 
           WHEN amount >= 200 THEN 'High'
           WHEN amount BETWEEN 100 AND 199 THEN 'Medium'
           ELSE 'Low'
       END AS amount_category
FROM new_payments;

SELECT customer_id, payment_id, amount,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY amount DESC) AS row_num
FROM new_payments;


SELECT customer_id, SUM(amount) AS total_paid,
       RANK() OVER (ORDER BY SUM(amount) DESC) AS rank_position
FROM new_payments
GROUP BY customer_id;

SELECT title, price,
       DENSE_RANK() OVER (ORDER BY price DESC) AS price_rank
FROM new_products;

SELECT customer_id, payment_id, amount,
       LEAD(amount) OVER (PARTITION BY customer_id ORDER BY payment_id) AS next_payment
FROM new_payments;

SELECT customer_id, payment_id, amount,
       LAG(amount) OVER (PARTITION BY customer_id ORDER BY payment_id) AS previous_payment
FROM new_payments;
