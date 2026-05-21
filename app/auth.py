import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status

JWT_SECRET = os.environ.get("HOTEL_JWT_SECRET", "dev-insecure-secret-change-me-in-production-please")
JWT_ALGO = "HS256"
STAFF_TOKEN_TTL_DAYS = 30
CUSTOMER_SESSION_TTL_HOURS = 4


def hash_license_key(key: str) -> str:
    return bcrypt.hashpw(key.encode(), bcrypt.gensalt()).decode()


def verify_license_key(key: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(key.encode(), hashed.encode())
    except ValueError:
        return False


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def issue_user_token(cafe_id: int, user_id: int, role: str, email: str) -> str:
    if role not in ("admin", "staff"):
        raise ValueError(f"invalid role: {role}")
    payload = {
        "cafe_id": cafe_id,
        "user_id": user_id,
        "role": role,
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + STAFF_TOKEN_TTL_DAYS * 24 * 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def issue_staff_token(cafe_id: int) -> str:
    # legacy helper kept for /auth/activate (bootstrap returns an admin token)
    return issue_user_token(cafe_id, user_id=0, role="admin", email="bootstrap@activate")


def decode_staff_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token: {exc}")


def new_session_token() -> str:
    return secrets.token_hex(32)


def session_expiry() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=CUSTOMER_SESSION_TTL_HOURS)).strftime("%Y-%m-%dT%H:%M:%S")


def _read_bearer(authorization: Optional[str]) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    return decode_staff_token(token)


def require_staff_or_admin(authorization: Optional[str] = Header(default=None)) -> dict:
    claims = _read_bearer(authorization)
    if claims.get("role") not in ("staff", "admin"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "role not permitted")
    return claims


def require_admin(authorization: Optional[str] = Header(default=None)) -> dict:
    claims = _read_bearer(authorization)
    if claims.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin role required")
    return claims


# Legacy: existing routers use these. Now permit both staff and admin.
require_staff = require_staff_or_admin


def staff_cafe_id(claims: dict = Depends(require_staff_or_admin)) -> int:
    return int(claims["cafe_id"])


def admin_cafe_id(claims: dict = Depends(require_admin)) -> int:
    return int(claims["cafe_id"])


def require_customer_session(x_session_token: Optional[str] = Header(default=None)) -> str:
    if not x_session_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing X-Session-Token header")
    return x_session_token
