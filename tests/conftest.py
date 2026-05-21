import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app import auth as auth_mod
from app.db import Database, set_db
from app.main import create_app


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture
def app(db_path):
    db = Database(path=db_path)
    db.init_schema()
    set_db(db)
    return create_app()


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


def make_cafe(db_path: str, name: str, license_key: str) -> int:
    db = Database(path=db_path)
    conn = db.connect()
    try:
        cur = conn.execute(
            "INSERT INTO cafes (name, license_key_hash) VALUES (?, ?)",
            (name, auth_mod.hash_license_key(license_key)),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def seed_basic_menu(db_path: str, cafe_id: int) -> dict:
    db = Database(path=db_path)
    conn = db.connect()
    try:
        cur = conn.execute(
            "INSERT INTO menu_categories (cafe_id, name, sort_order) VALUES (?, 'Starters', 0)",
            (cafe_id,),
        )
        cat_id = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO menu_items (cafe_id, category_id, name, description, price) VALUES (?, ?, 'Samosa', '', 50)",
            (cafe_id, cat_id),
        )
        item1 = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO menu_items (cafe_id, category_id, name, description, price) VALUES (?, ?, 'Spring Roll', '', 80)",
            (cafe_id, cat_id),
        )
        item2 = cur.lastrowid
        cur = conn.execute("INSERT INTO tables (cafe_id, table_number) VALUES (?, 'T1')", (cafe_id,))
        table1 = cur.lastrowid
        cur = conn.execute("INSERT INTO tables (cafe_id, table_number) VALUES (?, 'T2')", (cafe_id,))
        table2 = cur.lastrowid
        conn.commit()
        return {"category_id": cat_id, "item1": item1, "item2": item2, "table1": table1, "table2": table2}
    finally:
        conn.close()


@pytest.fixture
def cafe(db_path):
    cafe_id = make_cafe(db_path, "Demo Cafe", "license-A")
    ids = seed_basic_menu(db_path, cafe_id)
    return {"cafe_id": cafe_id, "license_key": "license-A", **ids}


def _bootstrap_admin(client, license_key: str, email="owner@cafe.test", password="owner1234") -> str:
    r = client.post("/auth/activate", json={
        "license_key": license_key,
        "admin_email": email,
        "admin_password": password,
    })
    assert r.status_code == 200, r.text
    return r.json()["staff_token"]


@pytest.fixture
def admin_token(client, cafe):
    return _bootstrap_admin(client, cafe["license_key"])


@pytest.fixture
def staff_token(client, cafe):
    # Existing tests use this fixture and expect admin-level capabilities (legacy v1 model).
    # We bootstrap the cafe as admin so those tests still pass.
    return _bootstrap_admin(client, cafe["license_key"])


@pytest.fixture
def staff_token_only(client, admin_token):
    """A pure-staff role token (created via admin's user-management endpoint)."""
    r = client.post(
        "/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "waiter@cafe.test", "password": "waiter1234", "role": "staff"},
    )
    assert r.status_code == 201, r.text
    login = client.post("/auth/login", json={"email": "waiter@cafe.test", "password": "waiter1234"})
    assert login.status_code == 200, login.text
    return login.json()["token"]
