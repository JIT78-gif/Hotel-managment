import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app import auth as auth_mod
from app.db import get_conn
from app.models import (
    CheckinRequest,
    CheckinResponse,
    MenuCategoryOut,
    MenuItemOut,
    MenuOut,
    OrderItemOut,
    PlaceOrderRequest,
    PlaceOrderResponse,
)
from app.realtime import manager

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/customer", tags=["customer"])


def _load_session(conn, token: str):
    row = conn.execute(
        "SELECT token, cafe_id, table_id, name, phone, expires_at FROM customer_sessions WHERE token = ?",
        (token,),
    ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid session token")
    return row


@router.post("/checkin", response_model=CheckinResponse)
@limiter.limit("10/minute")
def checkin(request: Request, req: CheckinRequest, conn=Depends(get_conn)):
    cafe = conn.execute("SELECT id FROM cafes WHERE id = ?", (req.cafe_id,)).fetchone()
    if not cafe:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "cafe not found")

    # Resolve table: prefer table_number (user-typed), fall back to table_id (legacy)
    table_id = None
    table_number = None
    if req.table_number:
        tn = req.table_number.strip()
        if not tn:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "table_number is empty")
        existing = conn.execute(
            "SELECT id, table_number FROM tables WHERE cafe_id = ? AND table_number = ?",
            (req.cafe_id, tn),
        ).fetchone()
        if existing:
            table_id = existing["id"]
            table_number = existing["table_number"]
        else:
            # Auto-create on first sight so guests don't get stuck at unknown tables
            try:
                cur = conn.execute(
                    "INSERT INTO tables (cafe_id, table_number) VALUES (?, ?)",
                    (req.cafe_id, tn),
                )
                conn.commit()
                table_id = cur.lastrowid
                table_number = tn
            except sqlite3.IntegrityError:
                row = conn.execute(
                    "SELECT id, table_number FROM tables WHERE cafe_id = ? AND table_number = ?",
                    (req.cafe_id, tn),
                ).fetchone()
                if not row:
                    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "could not create table")
                table_id = row["id"]
                table_number = row["table_number"]
    elif req.table_id is not None:
        existing = conn.execute(
            "SELECT id, table_number FROM tables WHERE id = ? AND cafe_id = ?",
            (req.table_id, req.cafe_id),
        ).fetchone()
        if not existing:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "table not found at this cafe")
        table_id = existing["id"]
        table_number = existing["table_number"]
    else:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "either table_number or table_id must be provided",
        )

    token = auth_mod.new_session_token()
    expires = auth_mod.session_expiry()
    conn.execute(
        "INSERT INTO customer_sessions (token, cafe_id, table_id, name, phone, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
        (token, req.cafe_id, table_id, req.name, req.phone, expires),
    )
    conn.commit()
    return CheckinResponse(
        session_token=token, expires_at=expires,
        table_id=table_id, table_number=table_number,
    )


@router.get("/menu", response_model=MenuOut)
def menu(
    conn=Depends(get_conn),
    session_token: str = Depends(auth_mod.require_customer_session),
):
    session = _load_session(conn, session_token)
    cafe_id = session["cafe_id"]
    cats = conn.execute(
        "SELECT id, name, sort_order FROM menu_categories WHERE cafe_id = ? ORDER BY sort_order, id",
        (cafe_id,),
    ).fetchall()
    items_by_cat: dict[int, list[MenuItemOut]] = {c["id"]: [] for c in cats}
    items = conn.execute(
        "SELECT id, category_id, name, description, price, image_url, is_available FROM menu_items "
        "WHERE cafe_id = ? AND is_available = 1 ORDER BY id",
        (cafe_id,),
    ).fetchall()
    for it in items:
        items_by_cat.setdefault(it["category_id"], []).append(
            MenuItemOut(
                id=it["id"], name=it["name"], description=it["description"],
                price=it["price"], image_url=it["image_url"] or "",
                is_available=bool(it["is_available"]),
                category_id=it["category_id"],
            )
        )
    categories = [
        MenuCategoryOut(id=c["id"], name=c["name"], sort_order=c["sort_order"], items=items_by_cat.get(c["id"], []))
        for c in cats
    ]
    return MenuOut(categories=categories)


@router.post("/orders", response_model=PlaceOrderResponse)
async def place_order(
    req: PlaceOrderRequest,
    conn=Depends(get_conn),
    session_token: str = Depends(auth_mod.require_customer_session),
):
    session = _load_session(conn, session_token)
    cafe_id = session["cafe_id"]
    table_id = session["table_id"]

    item_ids = [i.menu_item_id for i in req.items]
    placeholders = ",".join(["?"] * len(item_ids))
    rows = conn.execute(
        f"SELECT id, name, price, is_available FROM menu_items WHERE cafe_id = ? AND id IN ({placeholders})",
        (cafe_id, *item_ids),
    ).fetchall()
    by_id = {r["id"]: r for r in rows}

    snapshots = []
    total = 0.0
    for item in req.items:
        m = by_id.get(item.menu_item_id)
        if not m:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"menu item {item.menu_item_id} not found")
        if not m["is_available"]:
            raise HTTPException(status.HTTP_409_CONFLICT, f"item {m['name']} is unavailable")
        snapshots.append((m["id"], m["name"], m["price"], item.quantity))
        total += m["price"] * item.quantity

    cur = conn.execute(
        "INSERT INTO orders (cafe_id, table_id, session_token, status, total_amount) VALUES (?, ?, ?, 'placed', ?)",
        (cafe_id, table_id, session_token, total),
    )
    order_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO order_items (order_id, menu_item_id, name_snapshot, price_snapshot, quantity) VALUES (?, ?, ?, ?, ?)",
        [(order_id, mid, name, price, qty) for (mid, name, price, qty) in snapshots],
    )
    conn.commit()

    table_row = conn.execute("SELECT table_number FROM tables WHERE id = ?", (table_id,)).fetchone()
    payload = {
        "event": "new_order",
        "order": {
            "id": order_id,
            "table_id": table_id,
            "table_number": table_row["table_number"] if table_row else "",
            "customer_name": session["name"],
            "status": "placed",
            "total_amount": total,
            "items": [
                OrderItemOut(menu_item_id=mid, name=name, price=price, quantity=qty).model_dump()
                for (mid, name, price, qty) in snapshots
            ],
        },
    }
    await manager.broadcast(cafe_id, payload)

    return PlaceOrderResponse(order_id=order_id, total_amount=total, status="placed")


def _customer_order_view(conn, row) -> dict:
    items = conn.execute(
        "SELECT menu_item_id, name_snapshot, price_snapshot, quantity FROM order_items WHERE order_id = ?",
        (row["id"],),
    ).fetchall()
    return {
        "id": row["id"],
        "status": row["status"],
        "total_amount": row["total_amount"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "items": [
            {"menu_item_id": i["menu_item_id"], "name": i["name_snapshot"],
             "price": i["price_snapshot"], "quantity": i["quantity"]}
            for i in items
        ],
    }


@router.get("/orders")
def list_my_orders(
    conn=Depends(get_conn),
    session_token: str = Depends(auth_mod.require_customer_session),
):
    _load_session(conn, session_token)
    rows = conn.execute(
        "SELECT * FROM orders WHERE session_token = ? ORDER BY created_at DESC",
        (session_token,),
    ).fetchall()
    return [_customer_order_view(conn, r) for r in rows]


@router.get("/orders/{order_id}")
def get_my_order(
    order_id: int,
    conn=Depends(get_conn),
    session_token: str = Depends(auth_mod.require_customer_session),
):
    _load_session(conn, session_token)
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not row or row["session_token"] != session_token:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")
    return _customer_order_view(conn, row)
