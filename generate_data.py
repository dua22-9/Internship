# generate_data.py
# This script generates fake CSV data for our ETL pipeline
# Using the Faker library to create realistic-looking data
# Some rows are intentionally "dirty" so we can test our data cleaning later

import os
import random
import sys
from datetime import datetime, timedelta
import pandas as pd
from faker import Faker

sys.stdout.reconfigure(encoding="utf-8")

fake = Faker()
Faker.seed(42)
random.seed(42)

# where to save the csvs
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(output_dir, exist_ok=True)

categories = ["Electronics", "Clothing", "Home & Kitchen", "Books", "Sports"]
valid_statuses = ["completed", "pending", "cancelled", "shipped"]
invalid_statuses = ["refunded", "unknown", "???", ""]  # these will be used to create bad data

today = datetime.today().date()


# Generate Customers
def generate_customers(n=350):
    rows = []
    used_ids = []

    for i in range(1, n + 1):
        # sometimes duplicate an ID (~3% chance) to test duplicate handling
        if used_ids and random.random() < 0.03:
            cid = random.choice(used_ids)
        else:
            cid = i
        used_ids.append(cid)

        # mess up some emails - null or missing @ sign
        r = random.random()
        if r < 0.05:
            email = None  # null email
        elif r < 0.08:
            email = fake.user_name()  # no @ sign so its malformed
        else:
            email = fake.email()

        # some signup dates in the future (which shouldnt be possible)
        if random.random() < 0.04:
            signup = today + timedelta(days=random.randint(1, 365))
        else:
            signup = fake.date_between(start_date="-2y", end_date="today")

        rows.append({
            "customer_id": cid,
            "name": fake.name(),
            "email": email,
            "address": fake.address().replace('\n', ', '),
        })

    return pd.DataFrame(rows)


# Generate Products
def generate_products(n=100):
    rows = []
    used_names = []

    for i in range(1, n + 1):
        # duplicate some product names
        if used_names and random.random() < 0.04:
            name = random.choice(used_names)
        else:
            name = fake.catch_phrase()
        used_names.append(name)

        # some null categories
        category = None if random.random() < 0.05 else random.choice(categories)

        # some negative prices (bad data)
        if random.random() < 0.05:
            price = round(random.uniform(-50, -1), 2)
        else:
            price = round(random.uniform(5, 500), 2)

        stock = random.randint(0, 1000)

        rows.append({
            "product_id": i,
            "name": name,
            "category": category,
            "price": price,
        })

    return pd.DataFrame(rows)


# Generate Orders
def generate_orders(n=500, max_customer=350, max_product=100):
    rows = []

    for i in range(1, n + 1):
        # some orders reference customers/products that dont exist (orphan FKs)
        if random.random() < 0.04:
            cust_id = random.randint(max_customer + 1, max_customer + 200)
        else:
            cust_id = random.randint(1, max_customer)

        if random.random() < 0.04:
            prod_id = random.randint(max_product + 1, max_product + 100)
        else:
            prod_id = random.randint(1, max_product)

        # null quantities
        quantity = None if random.random() < 0.05 else random.randint(1, 10)

        # invalid statuses
        if random.random() < 0.05:
            status = random.choice(invalid_statuses)
        else:
            status = random.choice(valid_statuses)

        # negative totals
        if random.random() < 0.03:
            total = round(random.uniform(-500, -1), 2)
        else:
            total = round(random.uniform(10, 2000), 2)

        order_date = fake.date_between(start_date="-1y", end_date="today")

        rows.append({
            "order_id": i,
            "customer_id": cust_id,
            "product_id": prod_id,
            "quantity": quantity,
            "order_date": str(order_date),
            "status": status,
            "total_amount": total,
        })

    return pd.DataFrame(rows)


# Main
if __name__ == "__main__":
    print("Generating fake CSV data...")
    print()

    customers = generate_customers()
    products = generate_products()
    orders = generate_orders()

    customers.to_csv(os.path.join(output_dir, "customers_raw.csv"), index=False)
    products.to_csv(os.path.join(output_dir, "products_raw.csv"), index=False)
    orders.to_csv(os.path.join(output_dir, "orders_raw.csv"), index=False)

    print(f"customers_raw.csv: {len(customers)} rows")
    print(f"products_raw.csv: {len(products)} rows")
    print(f"orders_raw.csv: {len(orders)} rows")
    print(f"\nSaved to: {output_dir}")
