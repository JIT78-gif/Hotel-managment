import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app import auth as auth_mod
from app.db import get_conn
from app.models import (
    ActivateRequest,
    ActivateResponse,
    LoginRequest,
    LoginResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/activate", response_model=ActivateResponse)
def activate(req: ActivateRequest, conn=Depends(get_conn)):
    """Bootstrap a cafe: verify license key, create first admin user, return admin token.

    Idempotent only on email collision: if an admin with that email already exists
    for the cafe, return 409 (delete & reseed for a clean demo).
    """
    rows = conn.execute("SELECT id, name, license_key_hash FROM cafes").fetchall()
    cafe = None
    for row in rows:
        if auth_mod.verify_license_key(req.license_key, row["license_key_hash"]):
            cafe = row
            break
    if not cafe:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid license key")

    try:
        cur = conn.execute(
            "INSERT INTO users (cafe_id, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
            (cafe["id"], req.admin_email.lower(), auth_mod.hash_password(req.admin_password)),
        )
        conn.commit()
        user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "an admin with that email already exists for this cafe")

    token = auth_mod.issue_user_token(cafe["id"], user_id, "admin", req.admin_email.lower())
    return ActivateResponse(staff_token=token, cafe_id=cafe["id"], cafe_name=cafe["name"], role="admin")


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, conn=Depends(get_conn)):
    email = req.email.lower().strip()
    row = conn.execute(
        "SELECT u.id, u.cafe_id, u.email, u.password_hash, u.role, c.name AS cafe_name "
        "FROM users u JOIN cafes c ON c.id = u.cafe_id "
        "WHERE u.email = ?",
        (email,),
    ).fetchone()
    if not row or not auth_mod.verify_password(req.password, row["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid email or password")
    token = auth_mod.issue_user_token(row["cafe_id"], row["id"], row["role"], row["email"])
    return LoginResponse(
        token=token,
        cafe_id=row["cafe_id"],
        cafe_name=row["cafe_name"],
        role=row["role"],
        email=row["email"],
    )
