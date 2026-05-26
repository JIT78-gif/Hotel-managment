import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import auth as auth_mod
from app.auth import admin_cafe_id as staff_cafe_id  # admin-only for /admin/*
from app.db import get_conn
from app.models import (
    CafeInfo, CategoryIn, CategoryOut, CreateUserRequest, FeedbackOut,
    MenuItemIn, MenuItemOut, MenuItemUpdate, TableBillSummary, TableIn, TableInfo,
    TableOut, TableSessionInfo, UpdateGstRequest, UserOut,
)
from app.realtime import manager

router = APIRouter(prefix="/admin", tags=["admin"])


def _ensure_category(conn, cafe_id: int, category_id: int) -> None:
    row = conn.execute(
        "SELECT id FROM menu_categories WHERE id = ? AND cafe_id = ?",
        (category_id, cafe_id),
    ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "category not found in this cafe")


# Categories
@router.get("/categories", response_model=List[CategoryOut])
def list_categories(cafe_id: int = Depends(staff_cafe_id), conn=Depends(get_conn)):
    rows = conn.execute(
        "SELECT id, name, sort_order FROM menu_categories WHERE cafe_id = ? ORDER BY sort_order, id",
        (cafe_id,),
    ).fetchall()
    return [CategoryOut(id=r["id"], name=r["name"], sort_order=r["sort_order"]) for r in rows]


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(req: CategoryIn, cafe_id: int = Depends(staff_cafe_id), conn=Depends(get_conn)):
    cur = conn.execute(
        "INSERT INTO menu_categories (cafe_id, name, sort_order) VALUES (?, ?, ?)",
        (cafe_id, req.name, req.sort_order),
    )
    conn.commit()
    return CategoryOut(id=cur.lastrowid, name=req.name, sort_order=req.sort_order)


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, req: CategoryIn, cafe_id: int = Depends(staff_cafe_id), conn=Depends(get_conn)):
    _ensure_category(conn, cafe_id, category_id)
    conn.execute(
        "UPDATE menu_categories SET name = ?, sort_order = ? WHERE id = ?",
        (req.name, req.sort_order, category_id),
    )
    conn.commit()
    return CategoryOut(id=category_id, name=req.name, sort_order=req.sort_order)


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, cafe_id: int = Depends(staff_cafe_id), conn=Depends(get_conn)):
    _ensure_category(conn, cafe_id, category_id)
    conn.execute("DELETE FROM menu_categories WHERE id = ?", (category_id,))
    conn.commit()


# Menu items
def _menu_item_out(row) -> MenuItemOut:
    return MenuItemOut(
        id=row["id"], name=row["name"], description=row["description"],
        price=row["price"], image_url=row["image_url"] or "",
        is_available=bool(row["is_available"]),
        category_id=row["category_id"] if "category_id" in row.keys() else None,
    )


@router.get("/menu-items", response_model=List[MenuItemOut])
def list_items(cafe_id: int = Depends(staff_cafe_id), conn=Depends(get_conn)):
    rows = conn.execute(
        "SELECT id, category_id, name, description, price, image_url, is_available FROM menu_items WHERE cafe_id = ? ORDER BY id",
        (cafe_id,),
    ).fetchall()
    return [_menu_item_out(r) for r in rows]


@router.post("/menu-items", response_model=MenuItemOut, status_code=201)
def create_item(req: MenuItemIn, cafe_id: int = Depends(staff_cafe_id), conn=Depends(get_conn)):
    _ensure_category(conn, cafe_id, req.category_id)
    cur = conn.execute(
        "INSERT INTO menu_items (cafe_id, category_id, name, description, price, image_url, is_available) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (cafe_id, req.category_id, req.name, req.description, req.price, req.image_url, 1 if req.is_available else 0),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, category_id, name, description, price, image_url, is_available FROM menu_items WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    return _menu_item_out(row)


@router.patch("/menu-items/{item_id}", response_model=MenuItemOut)
def update_item(item_id: int, req: MenuItemUpdate, cafe_id: int = Depends(staff_cafe_id), conn=Depends(get_conn)):
    row = conn.execute(
        "SELECT id, cafe_id, category_id, name, description, price, image_url, is_available FROM menu_items WHERE id = ?",
        (item_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "menu item not found")
    if row["cafe_id"] != cafe_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "menu item belongs to a different cafe")

    new_cat = req.category_id if req.category_id is not None else row["category_id"]
    if req.category_id is not None:
        _ensure_category(conn, cafe_id, req.category_id)
    new_name = req.name if req.name is not None else row["name"]
    new_desc = req.description if req.description is not None else row["description"]
    new_price = req.price if req.price is not None else row["price"]
    new_img = req.image_url if req.image_url is not None else (row["image_url"] or "")
    new_avail = req.is_available if req.is_available is not None else bool(row["is_available"])

    conn.execute(
        "UPDATE menu_items SET category_id = ?, name = ?, description = ?, price = ?, image_url = ?, is_available = ? WHERE id = ?",
        (new_cat, new_name, new_desc, new_price, new_img, 1 if new_avail else 0, item_id),
    )
    conn.commit()
    new_row = conn.execute(
        "SELECT id, category_id, name, description, price, image_url, is_available FROM menu_items WHERE id = ?",
        (item_id,),
    ).fetchone()
    return _menu_item_out(new_row)


# Users (admin only — admin creates staff)
@router.get("/users", response_model=List[UserOut])
def list_users(cafe_id: int = Depends(staff_cafe_id), conn=Depends(get_conn)):
    rows = conn.execute(
        "SELECT id, email, role, created_at FROM users WHERE cafe_id = ? ORDER BY id",
        (cafe_id,),
    ).fetchall()
    return [UserOut(id=r["id"], email=r["email"], role=r["role"], created_at=r["created_at"]) for r in rows]


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(req: CreateUserRequest, cafe_id: int = Depends(staff_cafe_id), conn=Depends(get_conn)):
    try:
        cur = conn.execute(
            "INSERT INTO users (cafe_id, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (cafe_id, req.email.lower().strip(), auth_mod.hash_password(req.password), req.role),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "a user with that email already exists for this cafe")
    row = conn.execute(
        "SELECT id, email, role, created_at FROM users WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return UserOut(id=row["id"], email=row["email"], role=row["role"], created_at=row["created_at"])


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, claims: dict = Depends(auth_mod.require_admin), conn=Depends(get_conn)):
    if user_id == int(claims.get("user_id") or 0):
        raise HTTPException(status.HTTP_409_CONFLICT, "cannot delete your own account")
    row = conn.execute("SELECT cafe_id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    if row["cafe_id"] != int(claims["cafe_id"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "user belongs to a different cafe")
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()


@router.delete("/menu-items/{item_id}", status_code=204)
def delete_item(item_id: int, cafe_id: int = Depends(staff_cafe_id), conn=Depends(get_conn)):
    row = conn.execute("SELECT cafe_id FROM menu_items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "menu item not found")
    if row["cafe_id"] != cafe_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "menu item belongs to a different cafe")
    conn.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
    conn.commit()


# Tables
@router.get("/tables", response_model=List[TableInfo])
def list_tables(cafe_id: int = Depends(staff_cafe_id), conn=Depends(get_conn)):
    rows = conn.execute(
        "SELECT id, table_number, is_occupied FROM tables "
        "WHERE cafe_id = ? ORDER BY id",
        (cafe_id,),
    ).fetchall()
    out: List[TableInfo] = []
    for r in rows:
        info = TableInfo(
            id=r["id"],
            table_number=r["table_number"],
            is_occupied=bool(r["is_occupied"]),
        )
        # Only surface session data when the table is actually occupied.
        # This protects against legacy / orphaned unpaid sessions from earlier testing
        # showing up as ghost diners on idle tables.
        if not r["is_occupied"]:
            out.append(info)
            continue
        # Multi-person: aggregate across EVERY unpaid session at this table
        sessions = conn.execute(
            "SELECT token, name, phone, bill_requested, created_at FROM customer_sessions "
            "WHERE cafe_id = ? AND table_id = ? AND paid = 0 ORDER BY created_at",
            (cafe_id, r["id"]),
        ).fetchall()
        if sessions:
            primary = sessions[0]
            other_names = [s["name"] for s in sessions[1:]]
            display_name = primary["name"]
            if other_names:
                display_name = f"{primary['name']} + {len(other_names)} other" + ("s" if len(other_names) > 1 else "")
            any_bill_requested = any(bool(s["bill_requested"]) for s in sessions)
            info.session = TableSessionInfo(
                name=display_name,
                phone=primary["phone"],
                token=primary["token"],
                bill_requested=any_bill_requested,
                started_at=primary["created_at"],
                party_size=len(sessions),
            )
            tokens = [s["token"] for s in sessions]
            placeholders = ",".join("?" * len(tokens))
            bill_rows = conn.execute(
                f"SELECT total_amount, gst_amount FROM orders WHERE session_token IN ({placeholders})",
                tokens,
            ).fetchall()
            subtotal = sum(float(o["total_amount"]) for o in bill_rows)
            gst = sum(float(o["gst_amount"]) for o in bill_rows)
            item_count_row = conn.execute(
                f"SELECT COALESCE(SUM(quantity), 0) AS n FROM order_items "
                f"WHERE order_id IN (SELECT id FROM orders WHERE session_token IN ({placeholders}))",
                tokens,
            ).fetchone()
            info.bill = TableBillSummary(
                subtotal=round(subtotal, 2),
                gst_amount=round(gst, 2),
                grand_total=round(subtotal + gst, 2),
                order_count=len(bill_rows),
                item_count=int(item_count_row["n"] or 0),
            )
        out.append(info)
    return out


def _active_sessions_for_table(conn, cafe_id: int, table_id: int):
    """Every unpaid customer session currently dining at this table (multi-person).

    Returns an empty list if the table itself is not occupied — defensive
    against legacy orphaned sessions where `paid = 0` but the table was
    never properly closed (e.g., before mark-paid existed).
    """
    t = conn.execute(
        "SELECT is_occupied FROM tables WHERE id = ? AND cafe_id = ?",
        (table_id, cafe_id),
    ).fetchone()
    if not t or not t["is_occupied"]:
        return []
    return conn.execute(
        "SELECT token, name, phone, bill_requested, created_at FROM customer_sessions "
        "WHERE cafe_id = ? AND table_id = ? AND paid = 0 ORDER BY created_at",
        (cafe_id, table_id),
    ).fetchall()


@router.get("/tables/{table_id}/bill")
def get_table_bill(
    table_id: int,
    cafe_id: int = Depends(staff_cafe_id),
    conn=Depends(get_conn),
):
    """Combined bill across every person currently dining at this table."""
    row = conn.execute(
        "SELECT id, cafe_id, table_number FROM tables WHERE id = ?",
        (table_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "table not found")
    if row["cafe_id"] != cafe_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "table belongs to a different cafe")

    sessions = _active_sessions_for_table(conn, cafe_id, table_id)
    if not sessions:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no active session at this table")

    primary = sessions[0]
    other_names = [s["name"] for s in sessions[1:]]
    display_name = primary["name"]
    if other_names:
        display_name = f"{primary['name']} + {len(other_names)} other" + ("s" if len(other_names) > 1 else "")
    any_bill_requested = any(bool(s["bill_requested"]) for s in sessions)

    tokens = [s["token"] for s in sessions]
    placeholders = ",".join("?" * len(tokens))
    orders = conn.execute(
        f"SELECT id, session_token, status, total_amount, gst_rate, gst_amount, instructions, created_at "
        f"FROM orders WHERE session_token IN ({placeholders}) ORDER BY created_at",
        tokens,
    ).fetchall()

    # Map session token → name so admin can see WHO placed each order
    name_by_token = {s["token"]: s["name"] for s in sessions}

    detailed = []
    subtotal = 0.0
    gst_total = 0.0
    for o in orders:
        items = conn.execute(
            "SELECT name_snapshot, price_snapshot, quantity FROM order_items WHERE order_id = ?",
            (o["id"],),
        ).fetchall()
        detailed.append({
            "id": o["id"],
            "status": o["status"],
            "subtotal": float(o["total_amount"]),
            "gst_amount": float(o["gst_amount"]),
            "grand_total": round(float(o["total_amount"]) + float(o["gst_amount"]), 2),
            "instructions": o["instructions"] or "",
            "placed_by": name_by_token.get(o["session_token"], ""),
            "created_at": o["created_at"],
            "items": [
                {"name": i["name_snapshot"], "price": float(i["price_snapshot"]), "quantity": i["quantity"]}
                for i in items
            ],
        })
        subtotal += float(o["total_amount"])
        gst_total += float(o["gst_amount"])

    return {
        "table_id": table_id,
        "table_number": row["table_number"],
        "session": {
            "name": display_name,
            "phone": primary["phone"],
            "bill_requested": any_bill_requested,
            "started_at": primary["created_at"],
            "party_size": len(sessions),
        },
        "subtotal": round(subtotal, 2),
        "gst_amount": round(gst_total, 2),
        "grand_total": round(subtotal + gst_total, 2),
        "orders": detailed,
    }


@router.post("/tables/{table_id}/mark_paid")
async def mark_table_paid(
    table_id: int,
    cafe_id: int = Depends(staff_cafe_id),
    conn=Depends(get_conn),
):
    """Admin closes the table: marks every unpaid session paid, frees the table."""
    row = conn.execute(
        "SELECT id, cafe_id, table_number FROM tables WHERE id = ?",
        (table_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "table not found")
    if row["cafe_id"] != cafe_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "table belongs to a different cafe")

    sessions = _active_sessions_for_table(conn, cafe_id, table_id)
    if not sessions:
        raise HTTPException(status.HTTP_409_CONFLICT, "table is already idle")

    tokens = [s["token"] for s in sessions]
    placeholders = ",".join("?" * len(tokens))

    # Compute final totals before closing
    bill_rows = conn.execute(
        f"SELECT total_amount, gst_amount FROM orders WHERE session_token IN ({placeholders})",
        tokens,
    ).fetchall()
    subtotal = sum(float(o["total_amount"]) for o in bill_rows)
    gst = sum(float(o["gst_amount"]) for o in bill_rows)
    grand_total = round(subtotal + gst, 2)

    # Close ALL active sessions at this table
    conn.execute(
        f"UPDATE customer_sessions SET paid = 1, paid_at = datetime('now'), expires_at = datetime('now') "
        f"WHERE token IN ({placeholders})",
        tokens,
    )
    conn.execute(
        "UPDATE tables SET is_occupied = 0, current_session_token = NULL WHERE id = ?",
        (table_id,),
    )
    conn.commit()

    await manager.broadcast(cafe_id, {
        "event": "table_paid",
        "table": {
            "id": table_id,
            "table_number": row["table_number"],
            "session_tokens": tokens,
            "grand_total": grand_total,
            "party_size": len(sessions),
        },
    })
    return {
        "table_id": table_id,
        "subtotal": round(subtotal, 2),
        "gst_amount": round(gst, 2),
        "grand_total": grand_total,
        "party_size": len(sessions),
        "paid": True,
    }


# Cafe settings (GST rate)
@router.get("/cafe", response_model=CafeInfo)
def get_cafe(cafe_id: int = Depends(staff_cafe_id), conn=Depends(get_conn)):
    row = conn.execute("SELECT id, name, gst_rate FROM cafes WHERE id = ?", (cafe_id,)).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "cafe not found")
    return CafeInfo(id=row["id"], name=row["name"], gst_rate=float(row["gst_rate"]))


@router.patch("/cafe", response_model=CafeInfo)
def update_cafe(
    req: UpdateGstRequest,
    cafe_id: int = Depends(staff_cafe_id),
    conn=Depends(get_conn),
):
    conn.execute("UPDATE cafes SET gst_rate = ? WHERE id = ?", (req.gst_rate, cafe_id))
    conn.commit()
    row = conn.execute("SELECT id, name, gst_rate FROM cafes WHERE id = ?", (cafe_id,)).fetchone()
    return CafeInfo(id=row["id"], name=row["name"], gst_rate=float(row["gst_rate"]))


# Feedback — list customer feedback for this cafe
_FEEDBACK_PERIOD_CLAUSES = {
    "today": "AND date(created_at) = date('now', 'localtime')",
    "week":  "AND created_at >= datetime('now', '-7 days')",
    "month": "AND created_at >= datetime('now', '-30 days')",
    "all":   "",
}


@router.get("/feedback")
def list_feedback(
    period: Optional[str] = Query(default="all"),
    cafe_id: int = Depends(staff_cafe_id),
    conn=Depends(get_conn),
):
    if period and period not in _FEEDBACK_PERIOD_CLAUSES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid period")
    where = "WHERE cafe_id = ?"
    if period:
        where += " " + _FEEDBACK_PERIOD_CLAUSES[period]

    rows = conn.execute(
        f"SELECT id, table_number_snapshot AS table_number, customer_name, customer_phone, "
        f"       rating, comment, created_at "
        f"FROM feedback {where} ORDER BY created_at DESC, id DESC LIMIT 200",
        (cafe_id,),
    ).fetchall()

    # Summary stats — across the period
    stats_row = conn.execute(
        f"SELECT COUNT(*) AS n, AVG(rating) AS avg_rating FROM feedback {where}",
        (cafe_id,),
    ).fetchone()

    # Weekly average is always computed regardless of period filter
    week_row = conn.execute(
        "SELECT AVG(rating) AS avg_rating FROM feedback "
        "WHERE cafe_id = ? AND created_at >= datetime('now', '-7 days')",
        (cafe_id,),
    ).fetchone()

    return {
        "feedback": [
            {
                "id": r["id"],
                "table_number": r["table_number"],
                "customer_name": r["customer_name"],
                "customer_phone": r["customer_phone"],
                "rating": r["rating"],
                "comment": r["comment"] or "",
                "created_at": r["created_at"],
            }
            for r in rows
        ],
        "stats": {
            "count": int(stats_row["n"] or 0),
            "avg_rating": round(float(stats_row["avg_rating"]), 2) if stats_row["avg_rating"] else None,
            "week_avg_rating": round(float(week_row["avg_rating"]), 2) if week_row["avg_rating"] else None,
        },
    }


@router.post("/tables", response_model=TableOut, status_code=201)
def create_table(req: TableIn, cafe_id: int = Depends(staff_cafe_id), conn=Depends(get_conn)):
    try:
        cur = conn.execute(
            "INSERT INTO tables (cafe_id, table_number) VALUES (?, ?)",
            (cafe_id, req.table_number),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "table number already exists for this cafe")
    return TableOut(id=cur.lastrowid, table_number=req.table_number)


@router.delete("/tables/{table_id}", status_code=204)
def delete_table(table_id: int, cafe_id: int = Depends(staff_cafe_id), conn=Depends(get_conn)):
    row = conn.execute("SELECT cafe_id FROM tables WHERE id = ?", (table_id,)).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "table not found")
    if row["cafe_id"] != cafe_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "table belongs to a different cafe")
    conn.execute("DELETE FROM tables WHERE id = ?", (table_id,))
    conn.commit()
