"""One-shot script to bootstrap a demo cafe with admin user, menu (with images), and tables.

Run: python seed_demo.py
"""
import os
import secrets
import sys

from app import auth as auth_mod
from app.db import Database

DB_PATH = os.environ.get("HOTEL_DB_PATH", "app.db")
ADMIN_EMAIL = os.environ.get("DEMO_ADMIN_EMAIL", "admin@democafe.com")
ADMIN_PASSWORD = os.environ.get("DEMO_ADMIN_PASSWORD", "admin1234")
STAFF_EMAIL = os.environ.get("DEMO_STAFF_EMAIL", "staff@democafe.com")
STAFF_PASSWORD = os.environ.get("DEMO_STAFF_PASSWORD", "staff1234")

# Curated free Unsplash food photos (CC0 — Unsplash license).
# Each URL is the original Unsplash photo page id, rendered via images.unsplash.com.
_U = "https://images.unsplash.com/{photo_id}?w=800&auto=format&fit=crop&q=70"

MENU = {
    "Starters": [
        ("Crispy Samosa", "Golden potato-stuffed pastry, mint chutney",
         60, _U.format(photo_id="photo-1601050690597-df0568f70950")),
        ("Spring Roll", "Hand-rolled veg spring rolls, sweet chilli",
         90, _U.format(photo_id="photo-1606923829579-718061ce14b4")),
        ("Paneer Tikka", "Char-grilled cottage cheese, smoked paprika",
         240, _U.format(photo_id="photo-1567188040759-fb8a883dc6d8")),
        ("Hummus & Pita", "House hummus, warm sourdough pita, olive oil",
         210, _U.format(photo_id="photo-1542684415-bb4b3f9ab3d6")),
    ],
    "Soups": [
        ("Tomato Basil", "Slow-roasted tomato, garden basil, cream swirl",
         140, _U.format(photo_id="photo-1547592180-85f173990554")),
        ("Sweet Corn Veg", "Tender corn, julienned veg, white pepper",
         150, _U.format(photo_id="photo-1603105037303-c25e4f0a6e3e")),
    ],
    "Lunch": [
        ("Garden Thali", "Dal, sabzi, basmati rice, two rotis, salad",
         360, _U.format(photo_id="photo-1631452180519-c014fe946bc7")),
        ("Butter Chicken", "Slow-cooked tomato cream, two butter naan",
         460, _U.format(photo_id="photo-1565557623262-b51c2513a641")),
        ("Margherita Pizza", "San Marzano tomato, fior di latte, basil",
         390, _U.format(photo_id="photo-1574071318508-1cdbab80d002")),
    ],
    "Dinner": [
        ("Paneer Butter Masala", "Creamy tomato gravy, two butter naan",
         410, _U.format(photo_id="photo-1631452180775-fbf006eaff45")),
        ("Hyderabadi Biryani", "Saffron-scented basmati, raita, salan",
         420, _U.format(photo_id="photo-1563379091339-03b21ab4a4f8")),
        ("Lemon Herb Salmon", "Pan-seared salmon, sauteed greens, citrus",
         580, _U.format(photo_id="photo-1467003909585-2f8a72700288")),
    ],
    "Sweets": [
        ("Tiramisu", "Mascarpone, espresso-soaked savoiardi, cocoa",
         260, _U.format(photo_id="photo-1571877227200-a0d98ea607e9")),
        ("Gulab Jamun", "Warm milk dumplings in cardamom syrup",
         140, _U.format(photo_id="photo-1610508500445-a4592435e27e")),
    ],
    "Beverages": [
        ("Masala Chai", "House blend, ginger, cardamom, fresh milk",
         60, _U.format(photo_id="photo-1571934811356-5cc061b6821f")),
        ("Cold Brew", "12-hour single-origin cold brew, dash of milk",
         180, _U.format(photo_id="photo-1461023058943-07fcbe16d735")),
        ("Fresh Lime Soda", "Sweet or salted, served over crushed ice",
         110, _U.format(photo_id="photo-1556679343-c7306c1976bc")),
    ],
}


def main():
    db = Database(path=DB_PATH)
    db.init_schema()
    conn = db.connect()
    try:
        existing = conn.execute("SELECT id, name FROM cafes WHERE name = 'Demo Cafe'").fetchone()
        if existing:
            print(f"Demo Cafe already exists (id={existing['id']}). Delete {DB_PATH} to reseed.")
            sys.exit(0)

        license_key = f"cafe-{secrets.token_hex(8)}"
        cur = conn.execute(
            "INSERT INTO cafes (name, license_key_hash) VALUES (?, ?)",
            ("Demo Cafe", auth_mod.hash_license_key(license_key)),
        )
        cafe_id = cur.lastrowid

        # Admin user
        conn.execute(
            "INSERT INTO users (cafe_id, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
            (cafe_id, ADMIN_EMAIL, auth_mod.hash_password(ADMIN_PASSWORD)),
        )
        # Staff user
        conn.execute(
            "INSERT INTO users (cafe_id, email, password_hash, role) VALUES (?, ?, ?, 'staff')",
            (cafe_id, STAFF_EMAIL, auth_mod.hash_password(STAFF_PASSWORD)),
        )

        for table_num in ["T1", "T2", "T3", "T4", "T5", "T6"]:
            conn.execute(
                "INSERT INTO tables (cafe_id, table_number) VALUES (?, ?)",
                (cafe_id, table_num),
            )

        sort_order = 0
        for cat_name, items in MENU.items():
            cur = conn.execute(
                "INSERT INTO menu_categories (cafe_id, name, sort_order) VALUES (?, ?, ?)",
                (cafe_id, cat_name, sort_order),
            )
            cat_id = cur.lastrowid
            sort_order += 1
            for name, desc, price, image_url in items:
                conn.execute(
                    "INSERT INTO menu_items (cafe_id, category_id, name, description, price, image_url) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (cafe_id, cat_id, name, desc, price, image_url),
                )

        first_table = conn.execute(
            "SELECT id FROM tables WHERE cafe_id = ? ORDER BY id LIMIT 1", (cafe_id,)
        ).fetchone()
        conn.commit()

        print("=" * 64)
        print("Demo Cafe seeded.")
        print("=" * 64)
        print(f"cafe_id        : {cafe_id}")
        print(f"license_key    : {license_key}")
        print(f"admin login    : {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        print(f"staff login    : {STAFF_EMAIL} / {STAFF_PASSWORD}")
        print(f"sample table   : id={first_table['id']}")
        print()
        print("Frontend URLs (once `cd frontend && npm run dev` is running):")
        print(f"  Customer (QR)  http://localhost:3000/c/{cafe_id}/{first_table['id']}")
        print(f"  Staff/Admin    http://localhost:3000/login")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
