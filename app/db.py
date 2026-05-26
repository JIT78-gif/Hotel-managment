import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

DEFAULT_DB_PATH = os.environ.get("HOTEL_DB_PATH", "app.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS cafes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    license_key_hash TEXT NOT NULL UNIQUE,
    gst_rate REAL NOT NULL DEFAULT 5,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cafe_id INTEGER NOT NULL REFERENCES cafes(id) ON DELETE CASCADE,
    table_number TEXT NOT NULL,
    is_occupied INTEGER NOT NULL DEFAULT 0,
    current_session_token TEXT,
    UNIQUE (cafe_id, table_number)
);

CREATE TABLE IF NOT EXISTS menu_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cafe_id INTEGER NOT NULL REFERENCES cafes(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS menu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cafe_id INTEGER NOT NULL REFERENCES cafes(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES menu_categories(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price REAL NOT NULL,
    image_url TEXT NOT NULL DEFAULT '',
    is_available INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cafe_id INTEGER NOT NULL REFERENCES cafes(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin','staff')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (cafe_id, email)
);

CREATE TABLE IF NOT EXISTS customer_sessions (
    token TEXT PRIMARY KEY,
    cafe_id INTEGER NOT NULL REFERENCES cafes(id) ON DELETE CASCADE,
    table_id INTEGER NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    bill_requested INTEGER NOT NULL DEFAULT 0,
    paid INTEGER NOT NULL DEFAULT 0,
    paid_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cafe_id INTEGER NOT NULL REFERENCES cafes(id) ON DELETE CASCADE,
    table_id INTEGER NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
    session_token TEXT NOT NULL REFERENCES customer_sessions(token) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'placed',
    total_amount REAL NOT NULL,
    instructions TEXT NOT NULL DEFAULT '',
    gst_rate REAL NOT NULL DEFAULT 0,
    gst_amount REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    menu_item_id INTEGER NOT NULL REFERENCES menu_items(id),
    name_snapshot TEXT NOT NULL,
    price_snapshot REAL NOT NULL,
    quantity INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','ready','served'))
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cafe_id INTEGER NOT NULL REFERENCES cafes(id) ON DELETE CASCADE,
    session_token TEXT,
    table_number_snapshot TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_orders_cafe_status ON orders(cafe_id, status);
CREATE INDEX IF NOT EXISTS idx_menu_items_cafe_cat ON menu_items(cafe_id, category_id);
CREATE INDEX IF NOT EXISTS idx_feedback_cafe_created ON feedback(cafe_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_feedback_session ON feedback(session_token) WHERE session_token IS NOT NULL;
"""


class Database:
    def __init__(self, path: str = DEFAULT_DB_PATH):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

            def _cols(table: str) -> set[str]:
                return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}

            # Backwards-compat migrations for DBs that pre-date these columns
            if "image_url" not in _cols("menu_items"):
                conn.execute("ALTER TABLE menu_items ADD COLUMN image_url TEXT NOT NULL DEFAULT ''")

            cafes_cols = _cols("cafes")
            if "gst_rate" not in cafes_cols:
                conn.execute("ALTER TABLE cafes ADD COLUMN gst_rate REAL NOT NULL DEFAULT 5")

            tables_cols = _cols("tables")
            if "is_occupied" not in tables_cols:
                conn.execute("ALTER TABLE tables ADD COLUMN is_occupied INTEGER NOT NULL DEFAULT 0")
            if "current_session_token" not in tables_cols:
                conn.execute("ALTER TABLE tables ADD COLUMN current_session_token TEXT")

            sess_cols = _cols("customer_sessions")
            if "bill_requested" not in sess_cols:
                conn.execute("ALTER TABLE customer_sessions ADD COLUMN bill_requested INTEGER NOT NULL DEFAULT 0")
            if "paid" not in sess_cols:
                conn.execute("ALTER TABLE customer_sessions ADD COLUMN paid INTEGER NOT NULL DEFAULT 0")
            if "paid_at" not in sess_cols:
                conn.execute("ALTER TABLE customer_sessions ADD COLUMN paid_at TEXT")

            orders_cols = _cols("orders")
            if "instructions" not in orders_cols:
                conn.execute("ALTER TABLE orders ADD COLUMN instructions TEXT NOT NULL DEFAULT ''")
            if "gst_rate" not in orders_cols:
                conn.execute("ALTER TABLE orders ADD COLUMN gst_rate REAL NOT NULL DEFAULT 0")
            if "gst_amount" not in orders_cols:
                conn.execute("ALTER TABLE orders ADD COLUMN gst_amount REAL NOT NULL DEFAULT 0")

            order_items_cols = _cols("order_items")
            if "status" not in order_items_cols:
                # SQLite doesn't accept CHECK constraints in ADD COLUMN; the
                # constraint at table-creation time is sufficient for new DBs.
                conn.execute("ALTER TABLE order_items ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")

            # One-shot self-healing: close any unpaid sessions whose table is idle.
            # These are orphans from before mark-paid existed (the migration set
            # `paid = 0` as the default for every pre-existing row). Idempotent —
            # safe to run on every startup.
            conn.execute(
                "UPDATE customer_sessions SET paid = 1, paid_at = datetime('now') "
                "WHERE paid = 0 AND table_id IN "
                "(SELECT id FROM tables WHERE is_occupied = 0)"
            )

            conn.commit()


_db = Database()


def set_db(db: Database) -> None:
    global _db
    _db = db


def get_db() -> Database:
    return _db


def get_conn() -> Iterator[sqlite3.Connection]:
    conn = _db.connect()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def conn_ctx() -> Iterator[sqlite3.Connection]:
    conn = _db.connect()
    try:
        yield conn
    finally:
        conn.close()
