# export_report.py
# connects to postgres and exports a summary report CSV
# has 4 sections: revenue by category, top customers, order counts, month over month change

import os
import sys
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8")

base_dir = os.path.dirname(os.path.abspath(__file__))
reports_dir = os.path.join(base_dir, "reports")
os.makedirs(reports_dir, exist_ok=True)
report_file = os.path.join(reports_dir, "weekly_sales_report.csv")


def get_engine():
    load_dotenv(os.path.join(base_dir, ".env"))

    required = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        print(f"Missing env vars: {', '.join(missing)}")
        sys.exit(1)

    safe_password = urllib.parse.quote_plus(os.getenv('DB_PASSWORD'))
    url = (
        f"postgresql+psycopg2://{os.getenv('DB_USER')}:{safe_password}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    return create_engine(url, pool_pre_ping=True)


# the 4 queries 

# 1. total revenue per product category
query_revenue = """
SELECT p.category, SUM(o.total_amount) AS total_revenue
FROM orders o
JOIN products p ON o.product_id = p.product_id
WHERE o.status = 'completed'
GROUP BY p.category
ORDER BY total_revenue DESC;
"""

# 2. top 5 customers by how much they spent
query_top_customers = """
SELECT c.customer_id, c.name, SUM(o.total_amount) AS total_spent
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.status = 'completed'
GROUP BY c.customer_id, c.name
ORDER BY total_spent DESC
LIMIT 5;
"""

# 3. how many orders per status
query_status_counts = """
SELECT status, COUNT(*) AS order_count
FROM orders
GROUP BY status
ORDER BY order_count DESC;
"""

# 4. month over month revenue change using LAG (from week 1)
query_mom_revenue = """
SELECT
    TO_CHAR(order_date, 'YYYY-MM') AS month,
    SUM(total_amount) AS monthly_revenue,
    LAG(SUM(total_amount)) OVER (ORDER BY TO_CHAR(order_date, 'YYYY-MM')) AS prev_month_revenue,
    ROUND(
        (SUM(total_amount) - LAG(SUM(total_amount)) OVER (ORDER BY TO_CHAR(order_date, 'YYYY-MM')))
        / NULLIF(LAG(SUM(total_amount)) OVER (ORDER BY TO_CHAR(order_date, 'YYYY-MM')), 0) * 100,
        2
    ) AS revenue_change_pct
FROM orders
WHERE status = 'completed'
GROUP BY TO_CHAR(order_date, 'YYYY-MM')
ORDER BY month;
"""


if __name__ == "__main__":
    print("Generating weekly sales report...")
    print()

    engine = get_engine()
    print("Connected to PostgreSQL")

    # run each query and build the report
    sections = []

    df1 = pd.read_sql(query_revenue, engine)
    sections.append("=== Revenue by Product Category ===")
    sections.append(df1.to_csv(index=False))

    df2 = pd.read_sql(query_top_customers, engine)
    sections.append("=== Top 5 Customers by Spend ===")
    sections.append(df2.to_csv(index=False))

    df3 = pd.read_sql(query_status_counts, engine)
    sections.append("=== Orders Count by Status ===")
    sections.append(df3.to_csv(index=False))

    df4 = pd.read_sql(query_mom_revenue, engine)
    sections.append("=== Month-over-Month Revenue Change ===")
    sections.append(df4.to_csv(index=False))

    # write everything to one file
    report_content = "\n".join(sections)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"Report saved to: {report_file}")
    print()
    print(report_content)

    engine.dispose()
