"""Per-item ready/pending status — kitchen can mark each dish independently."""


def _place_order(client, cafe, item_qty=None):
    """Helper: check in + place an order with two different items."""
    if item_qty is None:
        item_qty = [(cafe["item1"], 1), (cafe["item2"], 1)]
    s = client.post("/customer/checkin", json={
        "cafe_id": cafe["cafe_id"],
        "table_id": cafe["table1"],
        "name": "Alice",
        "phone": "1111111111",
    }).json()["session_token"]
    r = client.post("/customer/orders", headers={"X-Session-Token": s}, json={
        "items": [{"menu_item_id": mid, "quantity": q} for mid, q in item_qty],
    })
    return s, r.json()["order_id"]


def test_items_start_as_pending(client, cafe, staff_token):
    s, oid = _place_order(client, cafe)
    h = {"Authorization": f"Bearer {staff_token}"}
    order = next(o for o in client.get("/staff/orders", headers=h).json() if o["id"] == oid)
    for item in order["items"]:
        assert item["status"] == "pending"
        assert item["item_id"] is not None


def test_marking_one_item_ready_promotes_order_to_preparing(client, cafe, staff_token):
    s, oid = _place_order(client, cafe)
    h = {"Authorization": f"Bearer {staff_token}"}
    order = next(o for o in client.get("/staff/orders", headers=h).json() if o["id"] == oid)
    assert order["status"] == "placed"

    first_item = order["items"][0]["item_id"]
    r = client.patch(
        f"/staff/orders/{oid}/items/{first_item}",
        headers=h, json={"status": "ready"},
    )
    assert r.status_code == 200, r.text
    updated = r.json()
    # Order has gone from 'placed' → 'preparing' (some items ready)
    assert updated["status"] == "preparing"
    ready_items = [i for i in updated["items"] if i["status"] == "ready"]
    assert len(ready_items) == 1


def test_marking_all_items_ready_promotes_order_to_ready(client, cafe, staff_token):
    s, oid = _place_order(client, cafe)
    h = {"Authorization": f"Bearer {staff_token}"}
    order = next(o for o in client.get("/staff/orders", headers=h).json() if o["id"] == oid)

    for item in order["items"]:
        r = client.patch(
            f"/staff/orders/{oid}/items/{item['item_id']}",
            headers=h, json={"status": "ready"},
        )
        assert r.status_code == 200

    final = r.json()
    assert final["status"] == "ready"
    assert all(i["status"] == "ready" for i in final["items"])


def test_unmarking_item_does_not_reverse_order_status(client, cafe, staff_token):
    """Moving an item back to pending after order auto-advanced to ready
    leaves the order status alone — order is forward-only."""
    s, oid = _place_order(client, cafe)
    h = {"Authorization": f"Bearer {staff_token}"}
    order = next(o for o in client.get("/staff/orders", headers=h).json() if o["id"] == oid)
    items = order["items"]

    # Mark all ready → order = "ready"
    for it in items:
        client.patch(f"/staff/orders/{oid}/items/{it['item_id']}", headers=h, json={"status": "ready"})

    # Toggle one back to pending
    r = client.patch(f"/staff/orders/{oid}/items/{items[0]['item_id']}", headers=h, json={"status": "pending"})
    assert r.status_code == 200
    # Order stays at "ready" — staff has to manually move it via /staff/orders/{id} PATCH
    # (forward-only state machine isn't broken by item toggles)
    assert r.json()["status"] == "ready"


def test_customer_sees_per_item_status(client, cafe, staff_token):
    s, oid = _place_order(client, cafe)
    h = {"Authorization": f"Bearer {staff_token}"}
    order = next(o for o in client.get("/staff/orders", headers=h).json() if o["id"] == oid)
    first_item = order["items"][0]["item_id"]
    client.patch(f"/staff/orders/{oid}/items/{first_item}", headers=h, json={"status": "ready"})

    cust = client.get("/customer/orders", headers={"X-Session-Token": s}).json()
    target = next(o for o in cust["orders"] if o["id"] == oid)
    statuses = sorted(i["status"] for i in target["items"])
    assert statuses == ["pending", "ready"]


def test_marking_all_items_served_advances_order_to_served(client, cafe, staff_token):
    s, oid = _place_order(client, cafe)
    h = {"Authorization": f"Bearer {staff_token}"}
    order = next(o for o in client.get("/staff/orders", headers=h).json() if o["id"] == oid)
    for item in order["items"]:
        r = client.patch(f"/staff/orders/{oid}/items/{item['item_id']}", headers=h, json={"status": "served"})
        assert r.status_code == 200
    assert r.json()["status"] == "served"


def test_partial_serve_keeps_order_in_ready(client, cafe, staff_token):
    """One item served + one item ready = order at 'ready' (NOT 'served' until all are served)."""
    s, oid = _place_order(client, cafe)
    h = {"Authorization": f"Bearer {staff_token}"}
    order = next(o for o in client.get("/staff/orders", headers=h).json() if o["id"] == oid)
    items = order["items"]

    # Item A served, item B ready → order should be 'ready' (all are at-least-ready)
    client.patch(f"/staff/orders/{oid}/items/{items[0]['item_id']}", headers=h, json={"status": "served"})
    r = client.patch(f"/staff/orders/{oid}/items/{items[1]['item_id']}", headers=h, json={"status": "ready"})
    assert r.status_code == 200
    updated = r.json()
    assert updated["status"] == "ready", "one served + one ready = order at 'ready', not 'served'"
    statuses = sorted(i["status"] for i in updated["items"])
    assert statuses == ["ready", "served"]


def test_partial_serve_with_pending_keeps_order_in_preparing(client, cafe, staff_token):
    """One item served + one still pending = order at 'preparing' (some started, not all ready)."""
    s, oid = _place_order(client, cafe)
    h = {"Authorization": f"Bearer {staff_token}"}
    order = next(o for o in client.get("/staff/orders", headers=h).json() if o["id"] == oid)
    items = order["items"]

    r = client.patch(f"/staff/orders/{oid}/items/{items[0]['item_id']}", headers=h, json={"status": "served"})
    assert r.json()["status"] == "preparing"


def test_cycle_back_does_not_regress_order_status(client, cafe, staff_token):
    """Once order auto-advances to 'served', toggling an item to ready/pending doesn't pull it back."""
    s, oid = _place_order(client, cafe)
    h = {"Authorization": f"Bearer {staff_token}"}
    order = next(o for o in client.get("/staff/orders", headers=h).json() if o["id"] == oid)
    items = order["items"]

    for it in items:
        client.patch(f"/staff/orders/{oid}/items/{it['item_id']}", headers=h, json={"status": "served"})

    # Cycle one item back to ready — order must STAY served
    r = client.patch(f"/staff/orders/{oid}/items/{items[0]['item_id']}", headers=h, json={"status": "ready"})
    assert r.status_code == 200
    assert r.json()["status"] == "served", "order must not regress to 'ready' after auto-advancing to 'served'"

    # Cycle back to pending too — still served
    r = client.patch(f"/staff/orders/{oid}/items/{items[0]['item_id']}", headers=h, json={"status": "pending"})
    assert r.json()["status"] == "served"


def test_manual_advance_to_served_syncs_all_items(client, cafe, staff_token):
    """When staff clicks the manual '→ Served' button, every item gets marked
    served too — so the customer's view stays consistent (no 'X items still
    on the way' while the order shows Served)."""
    s, oid = _place_order(client, cafe)
    h = {"Authorization": f"Bearer {staff_token}"}
    # Order starts with all items pending
    r = client.patch(f"/staff/orders/{oid}", headers=h, json={"status": "served"})
    assert r.status_code == 200, r.text
    final = r.json()
    assert final["status"] == "served"
    assert all(i["status"] == "served" for i in final["items"]), (
        "every item should be marked served when staff advances order to Served"
    )


def test_manual_advance_to_ready_promotes_pending_items_only(client, cafe, staff_token):
    """Advancing to 'ready' should promote pending items to ready, but keep
    items that were already served as served."""
    s, oid = _place_order(client, cafe)
    h = {"Authorization": f"Bearer {staff_token}"}
    # Pre-mark one item served; the other stays pending
    order = next(o for o in client.get("/staff/orders", headers=h).json() if o["id"] == oid)
    client.patch(f"/staff/orders/{oid}/items/{order['items'][0]['item_id']}",
                 headers=h, json={"status": "served"})

    # Manually advance the ORDER to ready
    r = client.patch(f"/staff/orders/{oid}", headers=h, json={"status": "ready"})
    assert r.status_code == 200, r.text
    statuses = sorted(i["status"] for i in r.json()["items"])
    assert statuses == ["ready", "served"], (
        "pending item should be promoted to ready; served item should stay served"
    )


def test_customer_sees_served_status(client, cafe, staff_token):
    s, oid = _place_order(client, cafe)
    h = {"Authorization": f"Bearer {staff_token}"}
    order = next(o for o in client.get("/staff/orders", headers=h).json() if o["id"] == oid)
    item_id = order["items"][0]["item_id"]
    client.patch(f"/staff/orders/{oid}/items/{item_id}", headers=h, json={"status": "served"})

    cust = client.get("/customer/orders", headers={"X-Session-Token": s}).json()
    target = next(o for o in cust["orders"] if o["id"] == oid)
    statuses = sorted(i["status"] for i in target["items"])
    assert "served" in statuses


def test_cross_order_item_id_rejected(client, cafe, staff_token):
    """Patching an item id that belongs to a different order returns 404."""
    sa, oid_a = _place_order(client, cafe)
    # Build a second order on the same table (just re-uses Alice's session)
    rb = client.post("/customer/orders", headers={"X-Session-Token": sa}, json={
        "items": [{"menu_item_id": cafe["item1"], "quantity": 1}],
    })
    oid_b = rb.json()["order_id"]

    h = {"Authorization": f"Bearer {staff_token}"}
    order_a = next(o for o in client.get("/staff/orders", headers=h).json() if o["id"] == oid_a)
    a_item = order_a["items"][0]["item_id"]

    # Try to patch order A's item via order B's URL
    r = client.patch(f"/staff/orders/{oid_b}/items/{a_item}", headers=h, json={"status": "ready"})
    assert r.status_code == 404
