#!/usr/bin/env python3
import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "database.db"

def create_tables(cur):
    # Drop tables if they already exist
    cur.execute("DROP TABLE IF EXISTS orders;")
    cur.execute("DROP TABLE IF EXISTS products;")
    cur.execute("DROP TABLE IF EXISTS users;")

    # Create users table
    cur.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            signup_date TEXT NOT NULL
        );
    """)

    # Create products table
    cur.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL
        );
    """)

    # Create orders table
    cur.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
    """)

def seed_users(cur, n=5):
    names = ["Alice", "Bob", "Charlie", "Diana", "Eve"]
    for name in names[:n]:
        email = f"{name.lower()}@example.com"
        # signup date: somewhere in the last 365 days
        days_ago = random.randint(1, 365)
        signup = (datetime.now() - timedelta(days=days_ago)).isoformat()
        cur.execute(
            "INSERT INTO users (name, email, signup_date) VALUES (?, ?, ?);",
            (name, email, signup)
        )

def seed_products(cur):
    products = [
        ("UltraWidget", 19.99),
        ("MegaGadget", 29.95),
        ("Thingamajig", 9.50),
        ("Doohickey", 14.75),
        ("Whatsit", 4.20),
    ]
    for name, price in products:
        cur.execute(
            "INSERT INTO products (name, price) VALUES (?, ?);",
            (name, price)
        )

def seed_orders(cur, n=20):
    # assume users 1–5 and products 1–5 exist
    for _ in range(n):
        user_id = random.randint(1, 5)
        product_id = random.randint(1, 5)
        qty = random.randint(1, 10)
        days_ago = random.randint(1, 180)
        order_date = (datetime.now() - timedelta(days=days_ago)).isoformat()
        cur.execute(
            "INSERT INTO orders (user_id, product_id, quantity, order_date) VALUES (?, ?, ?, ?);",
            (user_id, product_id, qty, order_date)
        )

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    create_tables(cur)
    seed_users(cur)
    seed_products(cur)
    seed_orders(cur)

    conn.commit()
    conn.close()
    print(f"Dummy database created: {DB_PATH}")

if __name__ == "__main__":
    main()
