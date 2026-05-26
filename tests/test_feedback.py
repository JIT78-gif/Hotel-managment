"""Customer feedback (5-star + comment) — submit, list, idempotency."""


def _checkin(client, cafe, name="Alice", phone="1111111111"):
    return client.post("/customer/checkin", json={
        "cafe_id": cafe["cafe_id"],
        "table_id": cafe["table1"],
        "name": name,
        "phone": phone,
    }).json()["session_token"]


def test_customer_can_submit_feedback(client, cafe, admin_token):
    sess = _checkin(client, cafe)
    r = client.post("/customer/feedback", headers={"X-Session-Token": sess}, json={
        "rating": 5, "comment": "great pizza!",
    })
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    assert r.json()["duplicate"] is False

    h = {"Authorization": f"Bearer {admin_token}"}
    body = client.get("/admin/feedback", headers=h).json()
    assert len(body["feedback"]) == 1
    fb = body["feedback"][0]
    assert fb["rating"] == 5
    assert fb["comment"] == "great pizza!"
    assert fb["customer_name"] == "Alice"
    assert fb["table_number"] == "T1"


def test_feedback_idempotent_per_session(client, cafe, admin_token):
    """Submitting twice with the same session token returns the existing row, not a new one."""
    sess = _checkin(client, cafe)
    r1 = client.post("/customer/feedback", headers={"X-Session-Token": sess}, json={"rating": 4, "comment": "good"})
    r2 = client.post("/customer/feedback", headers={"X-Session-Token": sess}, json={"rating": 1, "comment": "actually bad"})
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["duplicate"] is False
    assert r2.json()["duplicate"] is True
    assert r1.json()["id"] == r2.json()["id"]

    h = {"Authorization": f"Bearer {admin_token}"}
    body = client.get("/admin/feedback", headers=h).json()
    assert len(body["feedback"]) == 1
    # Original rating + comment preserved (the second attempt was ignored)
    assert body["feedback"][0]["rating"] == 4
    assert body["feedback"][0]["comment"] == "good"


def test_feedback_validates_rating_range(client, cafe):
    sess = _checkin(client, cafe)
    for bad in (0, 6, -1, 100):
        r = client.post("/customer/feedback", headers={"X-Session-Token": sess}, json={"rating": bad})
        assert r.status_code == 422, f"rating={bad} should be rejected"


def test_admin_feedback_summary_stats(client, cafe, admin_token):
    # Three sessions, three ratings
    for i, (name, phone, rating) in enumerate([
        ("Alice", "1111111111", 5),
        ("Bob",   "2222222222", 3),
        ("Carl",  "3333333333", 4),
    ]):
        sess = _checkin(client, cafe, name=name, phone=phone)
        client.post("/customer/feedback", headers={"X-Session-Token": sess}, json={"rating": rating})

    h = {"Authorization": f"Bearer {admin_token}"}
    body = client.get("/admin/feedback", headers=h).json()
    assert body["stats"]["count"] == 3
    assert body["stats"]["avg_rating"] == 4.0  # (5+3+4)/3
    assert body["feedback"][0]["customer_name"] == "Carl"  # newest first


def test_feedback_works_after_admin_marks_paid(client, cafe, admin_token):
    """Feedback typically arrives AFTER the session expires/is marked paid."""
    sess = _checkin(client, cafe)
    # Place + serve + bill flow
    r = client.post("/customer/orders", headers={"X-Session-Token": sess}, json={
        "items": [{"menu_item_id": cafe["item1"], "quantity": 1}],
    })
    order_id = r.json()["order_id"]
    h = {"Authorization": f"Bearer {admin_token}"}
    order = next(o for o in client.get("/staff/orders", headers=h).json() if o["id"] == order_id)
    for it in order["items"]:
        client.patch(f"/staff/orders/{order_id}/items/{it['item_id']}", headers=h, json={"status": "served"})
    client.post("/customer/request_bill", headers={"X-Session-Token": sess})

    tables = client.get("/admin/tables", headers=h).json()
    tid = next(t["id"] for t in tables if t["is_occupied"])
    client.post(f"/admin/tables/{tid}/mark_paid", headers=h)
    # Session is now marked paid + expires_at moved to now. Feedback should STILL work.
    fb = client.post("/customer/feedback", headers={"X-Session-Token": sess}, json={"rating": 5, "comment": "amazing"})
    assert fb.status_code == 200, fb.text
    assert fb.json()["ok"] is True
