"""Direct-SQLite version of the full menu reseed. Stop the backend before running.

This bypasses the API entirely and wipes everything cleanly:
  - order_items (so we don't violate FK)
  - orders
  - menu_items (cascade from categories)
  - menu_categories
…then inserts the full multi-cuisine menu.

Run (with backend STOPPED):
    python reseed_full_menu.py
"""
import os
import sqlite3
import sys

# Reuse the menu and image map from the API version so we don't duplicate.
from seed_full_menu import MENU, IMG  # noqa
from app.db import Database, DEFAULT_DB_PATH

DB_PATH = os.environ.get("HOTEL_DB_PATH", DEFAULT_DB_PATH)


def main() -> int:
    db = Database(path=DB_PATH)
    db.init_schema()
    try:
        conn = db.connect()
    except sqlite3.OperationalError as e:
        print(f"Could not open {DB_PATH}: {e}\nStop the backend (Ctrl+C) and try again.")
        return 1

    try:
        cafes = conn.execute("SELECT id, name FROM cafes ORDER BY id").fetchall()
        if not cafes:
            print("No cafes in DB. Run seed_demo.py first.")
            return 1
        cafe = cafes[0]
        cafe_id = cafe["id"]
        print(f"Reseeding into cafe {cafe_id}: {cafe['name']}")

        # Wipe orders first (order_items references menu_items, which would otherwise block CASCADE)
        n_oi = conn.execute("SELECT COUNT(*) AS n FROM order_items").fetchone()["n"]
        n_o = conn.execute("SELECT COUNT(*) AS n FROM orders WHERE cafe_id = ?", (cafe_id,)).fetchone()["n"]
        n_c = conn.execute("SELECT COUNT(*) AS n FROM menu_categories WHERE cafe_id = ?", (cafe_id,)).fetchone()["n"]
        n_i = conn.execute("SELECT COUNT(*) AS n FROM menu_items WHERE cafe_id = ?", (cafe_id,)).fetchone()["n"]
        print(f"Before wipe: {n_c} categories, {n_i} items, {n_o} orders, {n_oi} order_items")

        conn.execute("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE cafe_id = ?)", (cafe_id,))
        conn.execute("DELETE FROM orders WHERE cafe_id = ?", (cafe_id,))
        conn.execute("DELETE FROM menu_categories WHERE cafe_id = ?", (cafe_id,))
        # menu_items get wiped via CASCADE on menu_categories
        conn.commit()

        n_c2 = conn.execute("SELECT COUNT(*) AS n FROM menu_categories WHERE cafe_id = ?", (cafe_id,)).fetchone()["n"]
        n_i2 = conn.execute("SELECT COUNT(*) AS n FROM menu_items WHERE cafe_id = ?", (cafe_id,)).fetchone()["n"]
        print(f"After wipe: {n_c2} categories, {n_i2} items")

        # Insert new menu
        total = 0
        for sort_order, (cat_name, image_key, items) in enumerate(MENU):
            cur = conn.execute(
                "INSERT INTO menu_categories (cafe_id, name, sort_order) VALUES (?, ?, ?)",
                (cafe_id, cat_name, sort_order),
            )
            cat_id = cur.lastrowid
            img = IMG[image_key]
            for name, desc, price in items:
                conn.execute(
                    "INSERT INTO menu_items (cafe_id, category_id, name, description, price, image_url) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (cafe_id, cat_id, name, desc, price, img),
                )
                total += 1
        conn.commit()
        print(f"Inserted {len(MENU)} categories and {total} items.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
