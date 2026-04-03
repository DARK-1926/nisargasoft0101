#!/usr/bin/env python
"""Check how many sellers are captured for each product."""
import sqlite3
from pathlib import Path

db_path = Path("artifacts/live_monitor.db")

if not db_path.exists():
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all products
cursor.execute("SELECT asin, title FROM products")
products = cursor.fetchall()

print("=" * 80)
print("Seller Count Per Product")
print("=" * 80)
print()

for asin, title in products:
    # Count unique sellers for this ASIN
    cursor.execute("""
        SELECT COUNT(DISTINCT o.seller_id) as seller_count
        FROM offers o
        WHERE o.asin = ?
    """, (asin,))
    
    seller_count = cursor.fetchone()[0]
    
    # Get most recent capture time
    cursor.execute("""
        SELECT MAX(captured_at) as last_capture
        FROM offers
        WHERE asin = ?
    """, (asin,))
    
    last_capture = cursor.fetchone()[0]
    
    print(f"ASIN: {asin}")
    print(f"Title: {title[:60]}...")
    print(f"Unique Sellers Captured: {seller_count}")
    print(f"Last Captured: {last_capture}")
    print()

# Show recent seller names for the first product
if products:
    asin = products[0][0]
    cursor.execute("""
        SELECT DISTINCT s.name, o.price
        FROM offers o
        JOIN sellers s ON o.seller_id = s.seller_id
        WHERE o.asin = ?
        ORDER BY o.captured_at DESC
        LIMIT 20
    """, (asin,))
    
    sellers = cursor.fetchall()
    print("=" * 80)
    print(f"Recent Sellers for {asin}:")
    print("=" * 80)
    for seller_name, price in sellers:
        print(f"  - {seller_name}: ₹{price}")

conn.close()
