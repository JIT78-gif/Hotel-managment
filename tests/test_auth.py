def test_invalid_license_key_rejected(client, cafe):
    r = client.post("/auth/activate", json={
        "license_key": "totally-wrong",
        "admin_email": "x@y.test",
        "admin_password": "pwpwpwpw",
    })
    assert r.status_code == 401


def test_missing_staff_token_rejected(client):
    r = client.get("/staff/orders")
    assert r.status_code == 401


def test_invalid_session_token_rejected(client):
    r = client.get("/customer/menu", headers={"X-Session-Token": "garbage"})
    assert r.status_code == 401
