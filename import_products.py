import requests
import mysql.connector

# Fetch data from API
url = "https://fakestoreapi.com/products"
response = requests.get(url)
products = response.json()

# Connect to MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="yourpassword",
    database="day1"
)
cursor = conn.cursor()

# Insert into products table
for p in products:
    cursor.execute("""
        INSERT INTO products (product_id, title, price, description, category, image_url, rating_rate, rating_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        p["id"], p["title"], p["price"], p["description"],
        p["category"], p["image"], p["rating"]["rate"], p["rating"]["count"]
    ))

conn.commit()
cursor.close()
conn.close()
