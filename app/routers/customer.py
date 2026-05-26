import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app import auth as auth_mod
from app.db import get_conn
from app.models import (
    CheckinRequest,
    CheckinResponse,
    FeedbackIn,
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
        "SELECT * FROM customer_sessions WHERE token = ?",
        (token,),
    ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid session token")
    return row


def _normalize_table_key(s: str) -> str:
    """Canonical key for matching table numbers.

    "T1", "t1", "T 1", "1" all collapse to "1". This lets a customer type
    just "1" and still find the admin's "T1". Non-numeric (e.g. "VIP") keep
    their uppercased form.
    """
    s = (s or "").strip().upper().replace(" ", "")
    if s.startswith("T") and s[1:].isdigit():
        return s[1:]
    return s


def _find_table_smart(conn, cafe_id: int, typed: str):
    """Find a table at this cafe whose number matches the typed value under
    the normalized key. If multiple match, prefer the one with the T prefix
    (that's the admin's canonical form)."""
    key = _normalize_table_key(typed)
    rows = conn.execute(
        "SELECT id, table_number FROM tables WHERE cafe_id = ?",
        (cafe_id,),
    ).fetchall()
    matches = [r for r in rows if _normalize_table_key(r["table_number"]) == key]
    if not matches:
        return None
    # Prefer T-prefixed when duplicates exist (e.g. T1 wins over 1)
    matches.sort(key=lambda r: (
        not r["table_number"].upper().startswith("T"),
        r["id"],
    ))
    return matches[0]


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
        # Smart match: customer types "1" → finds "T1" (and vice versa).
        # Admin manages tables explicitly — we do NOT auto-create on unknown input.
        matched = _find_table_smart(conn, req.cafe_id, tn)
        if not matched:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Table '{tn}' not found at this cafe. Please double-check the number on your QR card or ask staff.",
            )
        table_id = matched["id"]
        table_number = matched["table_number"]
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

    # Resume: an unpaid session for this (cafe, table, phone) means this customer
    # closed the browser and came back. Return their existing token.
    phone = req.phone.strip()
    existing_session = conn.execute(
        "SELECT token, expires_at FROM customer_sessions "
        "WHERE cafe_id = ? AND table_id = ? AND phone = ? AND paid = 0 "
        "ORDER BY created_at DESC LIMIT 1",
        (req.cafe_id, table_id, phone),
    ).fetchone()
    if existing_session:
        return CheckinResponse(
            session_token=existing_session["token"],
            expires_at=existing_session["expires_at"],
            table_id=table_id, table_number=table_number,
        )

    # New session — but unlike a strict 1-phone-per-table policy, we ALLOW multiple
    # phones at the same table (real dining parties have multiple people). All their
    # orders combine into one bill, and admin marks the table paid once for everyone.
    token = auth_mod.new_session_token()
    expires = auth_mod.session_expiry()
    conn.execute(
        "INSERT INTO customer_sessions (token, cafe_id, table_id, name, phone, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
        (token, req.cafe_id, table_id, req.name, phone, expires),
    )
    # Mark the table occupied; current_session_token tracks the most recent joiner.
    # The billing query aggregates across ALL unpaid sessions at this table.
    conn.execute(
        "UPDATE tables SET is_occupied = 1, current_session_token = ? WHERE id = ?",
        (token, table_id),
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
    cafe = conn.execute(
        "SELECT name, gst_rate FROM cafes WHERE id = ?", (cafe_id,)
    ).fetchone()
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
    return MenuOut(
        categories=categories,
        gst_rate=float(cafe["gst_rate"]) if cafe else 0,
        cafe_name=cafe["name"] if cafe else "",
    )


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

    # Snapshot the cafe's GST rate onto the order so historical bills are stable
    cafe = conn.execute("SELECT gst_rate FROM cafes WHERE id = ?", (cafe_id,)).fetchone()
    gst_rate = float(cafe["gst_rate"]) if cafe else 0.0
    gst_amount = round(total * gst_rate / 100, 2)

    instructions = (req.instructions or "").strip()[:300]

    cur = conn.execute(
        "INSERT INTO orders (cafe_id, table_id, session_token, status, total_amount, instructions, gst_rate, gst_amount) "
        "VALUES (?, ?, ?, 'placed', ?, ?, ?, ?)",
        (cafe_id, table_id, session_token, total, instructions, gst_rate, gst_amount),
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
            "instructions": instructions,
            "gst_rate": gst_rate,
            "gst_amount": gst_amount,
            "items": [
                OrderItemOut(menu_item_id=mid, name=name, price=price, quantity=qty).model_dump()
                for (mid, name, price, qty) in snapshots
            ],
        },
    }
    await manager.broadcast(cafe_id, payload)

    return PlaceOrderResponse(
        order_id=order_id,
        total_amount=total,
        gst_amount=gst_amount,
        grand_total=round(total + gst_amount, 2),
        status="placed",
    )


def _customer_order_view(conn, row) -> dict:
    items = conn.execute(
        "SELECT id, menu_item_id, name_snapshot, price_snapshot, quantity, status "
        "FROM order_items WHERE order_id = ? ORDER BY id",
        (row["id"],),
    ).fetchall()
    subtotal = float(row["total_amount"])
    gst_rate = float(row["gst_rate"]) if "gst_rate" in row.keys() else 0.0
    gst_amount = float(row["gst_amount"]) if "gst_amount" in row.keys() else 0.0
    instructions = row["instructions"] if "instructions" in row.keys() else ""
    return {
        "id": row["id"],
        "status": row["status"],
        "total_amount": subtotal,
        "gst_rate": gst_rate,
        "gst_amount": gst_amount,
        "grand_total": round(subtotal + gst_amount, 2),
        "instructions": instructions,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "items": [
            {
                "item_id": i["id"],
                "menu_item_id": i["menu_item_id"],
                "name": i["name_snapshot"],
                "price": i["price_snapshot"],
                "quantity": i["quantity"],
                "status": (i["status"] if "status" in i.keys() else "pending") or "pending",
            }
            for i in items
        ],
    }


@router.get("/orders")
def list_my_orders(
    conn=Depends(get_conn),
    session_token: str = Depends(auth_mod.require_customer_session),
):
    sess = _load_session(conn, session_token)
    rows = conn.execute(
        "SELECT * FROM orders WHERE session_token = ? ORDER BY created_at DESC",
        (session_token,),
    ).fetchall()

    # Bill-gate visibility: the gate counts across EVERY unpaid session at the
    # table (multi-person party). The customer only sees their own orders, so
    # without this number their screen would say "all served" while the bill
    # request still 409s on another diner's pending items.
    table_unserved = conn.execute(
        "SELECT COUNT(*) AS n FROM order_items oi "
        "JOIN orders o ON o.id = oi.order_id "
        "WHERE o.session_token IN ("
        "  SELECT token FROM customer_sessions "
        "  WHERE cafe_id = ? AND table_id = ? AND paid = 0"
        ") AND oi.status != 'served'",
        (sess["cafe_id"], sess["table_id"]),
    ).fetchone()["n"]

    # Are any of those unserved items mine, or only at other seats?
    my_unserved = sum(
        1
        for r in rows
        for i in conn.execute(
            "SELECT status FROM order_items WHERE order_id = ?", (r["id"],)
        ).fetchall()
        if i["status"] != "served"
    )

    return {
        "session": {
            "bill_requested": bool(sess["bill_requested"]) if "bill_requested" in sess.keys() else False,
            "paid": bool(sess["paid"]) if "paid" in sess.keys() else False,
        },
        "table": {
            "unserved_count": int(table_unserved),
            "others_unserved_count": max(0, int(table_unserved) - my_unserved),
        },
        "orders": [_customer_order_view(conn, r) for r in rows],
    }


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


@router.post("/feedback")
def submit_feedback(
    req: FeedbackIn,
    conn=Depends(get_conn),
    # NOTE: we accept the session token here even when it's expired/paid —
    # feedback typically arrives AFTER the admin closes the bill.
    session_token: str = Depends(auth_mod.require_customer_session),
):
    sess = conn.execute(
        "SELECT * FROM customer_sessions WHERE token = ?", (session_token,)
    ).fetchone()
    if not sess:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid session token")

    # Idempotency — one feedback per session
    existing = conn.execute(
        "SELECT id FROM feedback WHERE session_token = ?", (session_token,)
    ).fetchone()
    if existing:
        return {"ok": True, "id": existing["id"], "duplicate": True}

    table = conn.execute(
        "SELECT table_number FROM tables WHERE id = ?", (sess["table_id"],)
    ).fetchone()

    cur = conn.execute(
        "INSERT INTO feedback (cafe_id, session_token, table_number_snapshot, "
        "customer_name, customer_phone, rating, comment) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            sess["cafe_id"], session_token,
            table["table_number"] if table else "",
            sess["name"], sess["phone"],
            req.rating, (req.comment or "").strip()[:500],
        ),
    )
    conn.commit()
    return {"ok": True, "id": cur.lastrowid, "duplicate": False}


@router.post("/request_bill")
async def request_bill(
    conn=Depends(get_conn),
    session_token: str = Depends(auth_mod.require_customer_session),
):
    session = _load_session(conn, session_token)
    cafe_id = session["cafe_id"]
    table_id = session["table_id"]

    # Hard gate: bill can only be requested once every item at this table —
    # across every unpaid session (multi-person party) — has been served.
    unserved = conn.execute(
        "SELECT COUNT(*) AS n FROM order_items oi "
        "JOIN orders o ON o.id = oi.order_id "
        "WHERE o.session_token IN ("
        "  SELECT token FROM customer_sessions "
        "  WHERE cafe_id = ? AND table_id = ? AND paid = 0"
        ") AND oi.status != 'served'",
        (cafe_id, table_id),
    ).fetchone()["n"]
    if unserved > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{unserved} item(s) still on the way — please wait until everything is served.",
        )

    conn.execute(
        "UPDATE customer_sessions SET bill_requested = 1 WHERE token = ?",
        (session_token,),
    )
    conn.commit()
    table_row = conn.execute("SELECT table_number FROM tables WHERE id = ?", (table_id,)).fetchone()
    await manager.broadcast(cafe_id, {
        "event": "bill_requested",
        "table": {
            "id": table_id,
            "table_number": table_row["table_number"] if table_row else "",
            "customer_name": session["name"],
        },
    })
    return {"bill_requested": True}
