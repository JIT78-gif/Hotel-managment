def test_staff_cannot_access_admin_routes(client, cafe, staff_token_only):
    h = {"Authorization": f"Bearer {staff_token_only}"}

    # Admin-only: create menu item
    r = client.post("/admin/menu-items", headers=h, json={
        "category_id": cafe["category_id"], "name": "X", "price": 10,
    })
    assert r.status_code == 403

    # Admin-only: create user
    r = client.post("/admin/users", headers=h, json={
        "email": "x@y.test", "password": "pwpwpwpw", "role": "staff",
    })
    assert r.status_code == 403

    # Admin-only: delete category
    r = client.delete(f"/admin/categories/{cafe['category_id']}", headers=h)
    assert r.status_code == 403


def test_staff_can_access_staff_routes(client, cafe, admin_token, staff_token_only):
    # Place an order so staff has something to see/update
    checkin = client.post("/customer/checkin", json={
        "cafe_id": cafe["cafe_id"], "table_id": cafe["table1"],
        "name": "Alice", "phone": "9999999999",
    }).json()
    sess = {"X-Session-Token": checkin["session_token"]}
    order = client.post("/customer/orders", headers=sess, json={
        "items": [{"menu_item_id": cafe["item1"], "quantity": 1}],
    }).json()

    h = {"Authorization": f"Bearer {staff_token_only}"}
    r = client.get("/staff/orders", headers=h)
    assert r.status_code == 200
    assert any(o["id"] == order["order_id"] for o in r.json())

    r = client.patch(f"/staff/orders/{order['order_id']}", headers=h, json={"status": "preparing"})
    assert r.status_code == 200


def test_login_works(client, cafe, admin_token):
    # The admin we bootstrapped via activate should be able to log in too.
    r = client.post("/auth/login", json={"email": "owner@cafe.test", "password": "owner1234"})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "admin"
    assert body["cafe_id"] == cafe["cafe_id"]
    assert body["email"] == "owner@cafe.test"


def test_wrong_password_rejected(client, cafe, admin_token):
    r = client.post("/auth/login", json={"email": "owner@cafe.test", "password": "wrong"})
    assert r.status_code == 401


def test_admin_cannot_delete_self(client, cafe, admin_token):
    # First create a staff user, then verify admin can delete them but not themselves.
    h = {"Authorization": f"Bearer {admin_token}"}
    r = client.post("/admin/users", headers=h, json={
        "email": "to_delete@cafe.test", "password": "pwpwpwpw", "role": "staff",
    })
    user_id = r.json()["id"]

    # Decode admin's own user_id from JWT
    import jwt
    from app.auth import JWT_SECRET, JWT_ALGO
    claims = jwt.decode(admin_token, JWT_SECRET, algorithms=[JWT_ALGO])
    admin_id = claims["user_id"]

    # Delete self → 409
    r = client.delete(f"/admin/users/{admin_id}", headers=h)
    assert r.status_code == 409

    # Delete the staff → 204
    r = client.delete(f"/admin/users/{user_id}", headers=h)
    assert r.status_code == 204
