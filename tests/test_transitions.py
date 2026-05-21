import pytest


@pytest.fixture
def placed_order_id(client, cafe, staff_token):
    checkin = client.post("/customer/checkin", json={
        "cafe_id": cafe["cafe_id"],
        "table_id": cafe["table1"],
        "name": "Carol",
        "phone": "6666666666",
    }).json()
    sess = {"X-Session-Token": checkin["session_token"]}
    r = client.post("/customer/orders", headers=sess, json={
        "items": [{"menu_item_id": cafe["item1"], "quantity": 1}],
    })
    return r.json()["order_id"]


def test_backward_transition_rejected(client, staff_token, placed_order_id):
    h = {"Authorization": f"Bearer {staff_token}"}
    client.patch(f"/staff/orders/{placed_order_id}", headers=h, json={"status": "preparing"})
    client.patch(f"/staff/orders/{placed_order_id}", headers=h, json={"status": "ready"})
    client.patch(f"/staff/orders/{placed_order_id}", headers=h, json={"status": "served"})

    r = client.patch(f"/staff/orders/{placed_order_id}", headers=h, json={"status": "placed"})
    assert r.status_code == 409


def test_same_state_rejected(client, staff_token, placed_order_id):
    h = {"Authorization": f"Bearer {staff_token}"}
    r = client.patch(f"/staff/orders/{placed_order_id}", headers=h, json={"status": "placed"})
    assert r.status_code == 409


def test_skip_forward_is_allowed(client, staff_token, placed_order_id):
    h = {"Authorization": f"Bearer {staff_token}"}
    r = client.patch(f"/staff/orders/{placed_order_id}", headers=h, json={"status": "ready"})
    assert r.status_code == 200
    assert r.json()["status"] == "ready"
