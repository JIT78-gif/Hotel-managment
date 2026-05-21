from tests.conftest import make_cafe, seed_basic_menu


def test_cafe_a_cannot_touch_cafe_b(client, db_path, cafe, staff_token):
    cafe_b_id = make_cafe(db_path, "Other Cafe", "license-B")
    b = seed_basic_menu(db_path, cafe_b_id)

    activate_b = client.post("/auth/activate", json={
        "license_key": "license-B",
        "admin_email": "owner@b.test",
        "admin_password": "owner1234",
    })
    assert activate_b.status_code == 200
    token_b = activate_b.json()["staff_token"]

    checkin_b = client.post("/customer/checkin", json={
        "cafe_id": cafe_b_id,
        "table_id": b["table1"],
        "name": "BobB",
        "phone": "7777777777",
    }).json()
    sess_b = {"X-Session-Token": checkin_b["session_token"]}
    order_b = client.post("/customer/orders", headers=sess_b, json={
        "items": [{"menu_item_id": b["item1"], "quantity": 1}],
    })
    assert order_b.status_code == 200
    order_b_id = order_b.json()["order_id"]

    h_a = {"Authorization": f"Bearer {staff_token}"}

    listed = client.get("/staff/orders", headers=h_a).json()
    assert all(o["id"] != order_b_id for o in listed)

    r = client.patch(f"/staff/orders/{order_b_id}", headers=h_a, json={"status": "preparing"})
    assert r.status_code == 403

    r = client.patch(f"/admin/menu-items/{b['item1']}", headers=h_a, json={"is_available": False})
    assert r.status_code == 403

    r = client.delete(f"/admin/tables/{b['table1']}", headers=h_a)
    assert r.status_code == 403


def test_customer_cannot_check_in_at_other_cafes_table(client, db_path, cafe):
    cafe_b_id = make_cafe(db_path, "Other Cafe", "license-B")
    b = seed_basic_menu(db_path, cafe_b_id)

    r = client.post("/customer/checkin", json={
        "cafe_id": cafe["cafe_id"],
        "table_id": b["table1"],
        "name": "Mallory",
        "phone": "1111111111",
    })
    assert r.status_code == 404
