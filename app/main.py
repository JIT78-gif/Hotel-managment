import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.auth import decode_staff_token
from app.db import get_db
from app.realtime import manager
from app.routers import admin, auth, customer, staff
from app.routers.customer import limiter


def _cors_origins() -> list[str]:
    raw = os.environ.get("HOTEL_CORS_ORIGINS", "*").strip()
    if raw == "*" or not raw:
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_db().init_schema()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Hotel Cafe Ordering API", version="0.1.0", lifespan=lifespan)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(customer.router)
    app.include_router(staff.router)
    app.include_router(admin.router)

    @app.websocket("/ws/staff")
    async def staff_ws(ws: WebSocket, token: str = Query(...)):
        try:
            claims = decode_staff_token(token)
        except HTTPException:
            await ws.close(code=4401)
            return
        if claims.get("role") not in ("staff", "admin"):
            await ws.close(code=4401)
            return
        cafe_id = int(claims["cafe_id"])
        await manager.connect(cafe_id, ws)
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await manager.disconnect(cafe_id, ws)

    @app.websocket("/ws/customer")
    async def customer_ws(ws: WebSocket, session_token: str = Query(...)):
        conn = get_db().connect()
        try:
            row = conn.execute(
                "SELECT cafe_id FROM customer_sessions WHERE token = ?", (session_token,)
            ).fetchone()
        finally:
            conn.close()
        if not row:
            await ws.close(code=4401)
            return
        cafe_id = int(row["cafe_id"])
        await manager.connect(cafe_id, ws)
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await manager.disconnect(cafe_id, ws)

    return app


app = create_app()
