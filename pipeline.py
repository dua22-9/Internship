import pandas as pd
import requests
import mysql.connector

resp = requests.get("https://fakestoreapi.com/products")
df = pd.DataFrame(resp.json())

df = df[['id','title','price','category']]
df['title'] = df['title'].str.strip()

conn = mysql.connector.connect(user="root", password="1234", host="localhost", database="day1")
cursor = conn.cursor()
for _, row in df.iterrows():
    cursor.execute("INSERT INTO new_products (product_id, title, price, category) VALUES (%s, %s, %s, %s)",
                   (row['id'], row['title'], row['price'], row['category']))
conn.commit()
conn.close()
