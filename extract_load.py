# extract_load.py
# ETL script - reads raw CSVs, cleans them, loads into PostgreSQL
# rejected/bad rows go to rejected_records.csv (dead letter pattern)

import os
import re
import sys
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8")

# load env variables
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "data")
rejected_csv = os.path.join(data_dir, "rejected_records.csv")

valid_statuses = {"completed", "pending", "cancelled", "shipped"}
email_pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_engine():
    """connect to postgres using .env file"""
    load_dotenv(os.path.join(base_dir, ".env"))

    required = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        print("Update your .env file first")
        sys.exit(1)

    safe_password = urllib.parse.quote_plus(os.getenv('DB_PASSWORD'))
    url = (
        f"postgresql+psycopg2://{os.getenv('DB_USER')}:{safe_password}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    # using connection pooling so we dont open a new connection every time
    engine = create_engine(url, pool_size=5, max_overflow=10, pool_pre_ping=True)
    return engine


def create_tables(engine):
    """create tables if they dont exist"""
    ddl = """
    DROP TABLE IF EXISTS orders CASCADE;
    DROP TABLE IF EXISTS products CASCADE;
    DROP TABLE IF EXISTS customers CASCADE;

    CREATE TABLE IF NOT EXISTS customers (
        customer_id   INT PRIMARY KEY,
        name          VARCHAR(100),
        email         VARCHAR(255) UNIQUE,
        address       VARCHAR(255)
    );

    CREATE TABLE IF NOT EXISTS products (
        product_id     INT PRIMARY KEY,
        name           VARCHAR(255),
        category       VARCHAR(100),
        price          DECIMAL(10, 2)
    );

    CREATE TABLE IF NOT EXISTS orders (
        order_id      INT PRIMARY KEY,
        customer_id   INT REFERENCES customers(customer_id),
        product_id    INT REFERENCES products(product_id),
        quantity      INT,
        order_date    DATE,
        status        VARCHAR(50),
        total_amount  DECIMAL(10, 2)
    );
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
    print("Tables created/verified")


# validation functions

def validate_customers(df):
    rejected = []
    today = datetime.today().date()

    # check for null primary keys
    mask = df["customer_id"].isna()
    rejected.append(df[mask].assign(source_table="customers", rejection_reason="Null customer_id"))
    df = df[~mask].copy()

    # duplicates - keep first one, reject the rest
    mask = df.duplicated(subset=["customer_id"], keep="first")
    rejected.append(df[mask].assign(source_table="customers", rejection_reason="Duplicate customer_id"))
    df = df[~mask].copy()

    # null emails
    mask = df["email"].isna() | (df["email"].astype(str).str.strip() == "")
    rejected.append(df[mask].assign(source_table="customers", rejection_reason="Null or empty email"))
    df = df[~mask].copy()

    # bad email format (missing @ or .)
    mask = ~df["email"].astype(str).apply(lambda e: bool(email_pattern.match(e)))
    rejected.append(df[mask].assign(source_table="customers", rejection_reason="Malformed email"))
    df = df[~mask].copy()

    # future signup dates removed as there is no signup_date in Week 1 schema

    rejected_df = pd.concat(rejected, ignore_index=True)
    return df, rejected_df


def validate_products(df):
    rejected = []

    # null pk
    mask = df["product_id"].isna()
    rejected.append(df[mask].assign(source_table="products", rejection_reason="Null product_id"))
    df = df[~mask].copy()

    # duplicate pk
    mask = df.duplicated(subset=["product_id"], keep="first")
    rejected.append(df[mask].assign(source_table="products", rejection_reason="Duplicate product_id"))
    df = df[~mask].copy()

    # null category
    mask = df["category"].isna() | (df["category"].astype(str).str.strip() == "")
    rejected.append(df[mask].assign(source_table="products", rejection_reason="Null category"))
    df = df[~mask].copy()

    # negative prices dont make sense
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    mask = df["price"] < 0
    rejected.append(df[mask].assign(source_table="products", rejection_reason="Negative price"))
    df = df[~mask].copy()

    rejected_df = pd.concat(rejected, ignore_index=True)
    return df, rejected_df


def validate_orders(df, valid_customer_ids, valid_product_ids):
    rejected = []

    # null pk
    mask = df["order_id"].isna()
    rejected.append(df[mask].assign(source_table="orders", rejection_reason="Null order_id"))
    df = df[~mask].copy()

    # duplicate pk
    mask = df.duplicated(subset=["order_id"], keep="first")
    rejected.append(df[mask].assign(source_table="orders", rejection_reason="Duplicate order_id"))
    df = df[~mask].copy()

    # null quantity
    mask = df["quantity"].isna()
    rejected.append(df[mask].assign(source_table="orders", rejection_reason="Null quantity"))
    df = df[~mask].copy()

    # invalid status values
    mask = ~df["status"].astype(str).str.lower().str.strip().isin(valid_statuses)
    rejected.append(df[mask].assign(source_table="orders", rejection_reason="Invalid status"))
    df = df[~mask].copy()

    # negative amounts
    df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce")
    mask = df["total_amount"] < 0
    rejected.append(df[mask].assign(source_table="orders", rejection_reason="Negative total_amount"))
    df = df[~mask].copy()

    # check if customer actually exists
    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce")
    mask = ~df["customer_id"].isin(valid_customer_ids)
    rejected.append(df[mask].assign(source_table="orders", rejection_reason="Orphan customer_id"))
    df = df[~mask].copy()

    # check if product actually exists
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce")
    mask = ~df["product_id"].isin(valid_product_ids)
    rejected.append(df[mask].assign(source_table="orders", rejection_reason="Orphan product_id"))
    df = df[~mask].copy()

    rejected_df = pd.concat(rejected, ignore_index=True)
    return df, rejected_df


# main script 

if __name__ == "__main__":
    print("=" * 50)
    print("  ETL Pipeline - Extract, Validate, Load")
    print("=" * 50)

    # connect to db
    engine = get_engine()
    print("Connected to PostgreSQL")

    create_tables(engine)

    # read the raw csvs
    print("\nReading CSV files...")
    customers_raw = pd.read_csv(os.path.join(data_dir, "customers_raw.csv"))
    products_raw = pd.read_csv(os.path.join(data_dir, "products_raw.csv"))
    orders_raw = pd.read_csv(os.path.join(data_dir, "orders_raw.csv"))

    print(f"  customers: {len(customers_raw)} rows")
    print(f"  products: {len(products_raw)} rows")
    print(f"  orders: {len(orders_raw)} rows")

    # validate everything
    print("\nValidating data...")
    all_rejected = []

    customers_clean, cust_rejected = validate_customers(customers_raw)
    all_rejected.append(cust_rejected)
    print(f"  Customers - accepted: {len(customers_clean)}, rejected: {len(cust_rejected)}")

    products_clean, prod_rejected = validate_products(products_raw)
    all_rejected.append(prod_rejected)
    print(f"  Products - accepted: {len(products_clean)}, rejected: {len(prod_rejected)}")

    # need the clean IDs to check foreign keys in orders
    valid_cust_ids = set(customers_clean["customer_id"].astype(int))
    valid_prod_ids = set(products_clean["product_id"].astype(int))

    orders_clean, ord_rejected = validate_orders(orders_raw, valid_cust_ids, valid_prod_ids)
    all_rejected.append(ord_rejected)
    print(f"  Orders - accepted: {len(orders_clean)}, rejected: {len(ord_rejected)}")

    # save all rejected rows to one file (dead letter pattern)
    rejected_all = pd.concat(all_rejected, ignore_index=True)
    if not rejected_all.empty:
        # put source_table and reason first so its easier to read
        cols = ["source_table", "rejection_reason"] + [c for c in rejected_all.columns if c not in ["source_table", "rejection_reason"]]
        rejected_all = rejected_all[cols]
        rejected_all.to_csv(rejected_csv, index=False)
        print(f"\n{len(rejected_all)} rejected rows saved to {rejected_csv}")

    # load into postgres
    print("\nLoading data into PostgreSQL...")

    # truncate first so we can re-run without duplicates
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE orders, products, customers CASCADE;"))
    print("  Truncated existing data")

    # fix data types before loading
    customers_clean["customer_id"] = customers_clean["customer_id"].astype(int)
    products_clean["product_id"] = products_clean["product_id"].astype(int)
    orders_clean["order_id"] = orders_clean["order_id"].astype(int)
    orders_clean["customer_id"] = orders_clean["customer_id"].astype(int)
    orders_clean["product_id"] = orders_clean["product_id"].astype(int)
    orders_clean["quantity"] = orders_clean["quantity"].astype(int)

    # load in order: customers first, then products, then orders (because of foreign keys)
    customers_clean.to_sql("customers", engine, if_exists="append", index=False, method="multi")
    print(f"  Loaded {len(customers_clean)} customers")

    products_clean.to_sql("products", engine, if_exists="append", index=False, method="multi")
    print(f"  Loaded {len(products_clean)} products")

    orders_clean.to_sql("orders", engine, if_exists="append", index=False, method="multi")
    print(f"  Loaded {len(orders_clean)} orders")

    # summary
    total_read = len(customers_raw) + len(products_raw) + len(orders_raw)
    total_loaded = len(customers_clean) + len(products_clean) + len(orders_clean)
    total_rejected = len(rejected_all)

    print(f"\n{'='*50}")
    print(f"Done! Read: {total_read}, Loaded: {total_loaded}, Rejected: {total_rejected}")
    print(f"{'='*50}")

    engine.dispose()
