def test_end_to_end_order_lifecycle(client, cafe, staff_token):
    checkin = client.post("/customer/checkin", json={
        "cafe_id": cafe["cafe_id"],
        "table_id": cafe["table1"],
        "name": "Alice",
        "phone": "9999999999",
    })
    assert checkin.status_code == 200, checkin.text
    session_token = checkin.json()["session_token"]
    sess_headers = {"X-Session-Token": session_token}

    menu = client.get("/customer/menu", headers=sess_headers)
    assert menu.status_code == 200
    cats = menu.json()["categories"]
    assert len(cats) == 1
    assert len(cats[0]["items"]) == 2

    with client.websocket_connect(f"/ws/staff?token={staff_token}") as ws:
        place = client.post("/customer/orders", headers=sess_headers, json={
            "items": [
                {"menu_item_id": cafe["item1"], "quantity": 2},
                {"menu_item_id": cafe["item2"], "quantity": 1},
            ],
        })
        assert place.status_code == 200, place.text
        body = place.json()
        order_id = body["order_id"]
        assert body["total_amount"] == 50 * 2 + 80
        assert body["status"] == "placed"

        new_order_msg = ws.receive_json()
        assert new_order_msg["event"] == "new_order"
        assert new_order_msg["order"]["id"] == order_id
        assert new_order_msg["order"]["customer_name"] == "Alice"
        assert new_order_msg["order"]["table_number"] == "T1"

        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        for next_status in ("preparing", "ready", "served"):
            r = client.patch(f"/staff/orders/{order_id}", headers=staff_headers, json={"status": next_status})
            assert r.status_code == 200, r.text
            assert r.json()["status"] == next_status
            evt = ws.receive_json()
            assert evt["event"] == "status_changed"
            assert evt["order"]["status"] == next_status

    listed = client.get("/staff/orders", headers={"Authorization": f"Bearer {staff_token}"})
    assert listed.status_code == 200
    found = [o for o in listed.json() if o["id"] == order_id]
    assert len(found) == 1
    assert found[0]["status"] == "served"


def test_admin_can_create_category_and_item(client, cafe, staff_token):
    h = {"Authorization": f"Bearer {staff_token}"}
    r = client.post("/admin/categories", headers=h, json={"name": "Soups", "sort_order": 1})
    assert r.status_code == 201
    cat_id = r.json()["id"]

    r = client.post("/admin/menu-items", headers=h, json={
        "category_id": cat_id, "name": "Tomato Soup", "price": 120,
    })
    assert r.status_code == 201
    assert r.json()["name"] == "Tomato Soup"

    items = client.get("/admin/menu-items", headers=h).json()
    assert any(i["name"] == "Tomato Soup" for i in items)


def test_unavailable_item_cannot_be_ordered(client, cafe, staff_token):
    h = {"Authorization": f"Bearer {staff_token}"}
    r = client.patch(f"/admin/menu-items/{cafe['item1']}", headers=h, json={"is_available": False})
    assert r.status_code == 200

    checkin = client.post("/customer/checkin", json={
        "cafe_id": cafe["cafe_id"],
        "table_id": cafe["table1"],
        "name": "Bob",
        "phone": "8888888888",
    }).json()
    sess = {"X-Session-Token": checkin["session_token"]}

    menu = client.get("/customer/menu", headers=sess).json()
    visible_ids = {i["id"] for c in menu["categories"] for i in c["items"]}
    assert cafe["item1"] not in visible_ids

    r = client.post("/customer/orders", headers=sess, json={
        "items": [{"menu_item_id": cafe["item1"], "quantity": 1}],
    })
    assert r.status_code == 409
