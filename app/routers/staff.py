from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import staff_cafe_id
from app.db import get_conn
from app.models import STATUS_ORDER, OrderItemOut, OrderOut, UpdateOrderItemRequest, UpdateOrderRequest
from app.realtime import manager

router = APIRouter(prefix="/staff", tags=["staff"])


def _hydrate_order(conn, row) -> OrderOut:
    items = conn.execute(
        "SELECT id, menu_item_id, name_snapshot, price_snapshot, quantity, status FROM order_items "
        "WHERE order_id = ? ORDER BY id",
        (row["id"],),
    ).fetchall()
    table = conn.execute("SELECT table_number FROM tables WHERE id = ?", (row["table_id"],)).fetchone()
    session = conn.execute("SELECT name FROM customer_sessions WHERE token = ?", (row["session_token"],)).fetchone()
    keys = row.keys()
    return OrderOut(
        id=row["id"],
        table_id=row["table_id"],
        table_number=table["table_number"] if table else "",
        customer_name=session["name"] if session else "",
        status=row["status"],
        total_amount=row["total_amount"],
        instructions=(row["instructions"] if "instructions" in keys else "") or "",
        gst_rate=float(row["gst_rate"]) if "gst_rate" in keys else 0.0,
        gst_amount=float(row["gst_amount"]) if "gst_amount" in keys else 0.0,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        items=[
            OrderItemOut(
                menu_item_id=i["menu_item_id"],
                name=i["name_snapshot"],
                price=i["price_snapshot"],
                quantity=i["quantity"],
                status=(i["status"] if "status" in i.keys() else "pending") or "pending",
                item_id=i["id"],
            )
            for i in items
        ],
    )


_PERIOD_CLAUSES = {
    "today": "AND date(created_at) = date('now', 'localtime')",
    "week":  "AND created_at >= datetime('now', '-7 days')",
    "month": "AND created_at >= datetime('now', '-30 days')",
    "all":   "",
}


@router.get("/orders", response_model=List[OrderOut])
def list_orders(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    period: Optional[str] = Query(default=None),
    cafe_id: int = Depends(staff_cafe_id),
    conn=Depends(get_conn),
):
    if status_filter and status_filter not in STATUS_ORDER:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid status")
    if period is not None and period not in _PERIOD_CLAUSES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid period")

    where = "WHERE cafe_id = ?"
    params: list = [cafe_id]
    if status_filter:
        where += " AND status = ?"
        params.append(status_filter)
    if period:
        where += " " + _PERIOD_CLAUSES[period]

    rows = conn.execute(
        f"SELECT * FROM orders {where} ORDER BY created_at DESC",
        params,
    ).fetchall()
    return [_hydrate_order(conn, r) for r in rows]


@router.patch("/orders/{order_id}", response_model=OrderOut)
async def update_order(
    order_id: int,
    req: UpdateOrderRequest,
    cafe_id: int = Depends(staff_cafe_id),
    conn=Depends(get_conn),
):
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")
    if row["cafe_id"] != cafe_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "order belongs to a different cafe")

    current_idx = STATUS_ORDER.index(row["status"])
    new_idx = STATUS_ORDER.index(req.status)
    if new_idx <= current_idx:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"cannot move from {row['status']} to {req.status} (forward-only)",
        )

    conn.execute(
        "UPDATE orders SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (req.status, order_id),
    )

    # Sync per-item statuses so the customer's view stays consistent with the
    # order's column. Staff using the manual advance button shouldn't leave
    # the customer staring at "1 item still on the way" when the order
    # appears Served on their phone.
    if req.status == "ready":
        # Promote any still-pending items to ready; preserve items already served.
        conn.execute(
            "UPDATE order_items SET status = 'ready' "
            "WHERE order_id = ? AND status = 'pending'",
            (order_id,),
        )
    elif req.status == "served":
        # Everything is delivered when the order column is marked Served.
        conn.execute(
            "UPDATE order_items SET status = 'served' WHERE order_id = ?",
            (order_id,),
        )
    conn.commit()

    new_row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    order = _hydrate_order(conn, new_row)
    await manager.broadcast(cafe_id, {"event": "status_changed", "order": order.model_dump()})
    return order


@router.patch("/orders/{order_id}/items/{item_id}", response_model=OrderOut)
async def update_order_item(
    order_id: int,
    item_id: int,
    req: UpdateOrderItemRequest,
    cafe_id: int = Depends(staff_cafe_id),
    conn=Depends(get_conn),
):
    """Toggle a single line item between 'pending' and 'ready'.

    When every line item on the order becomes 'ready', the order itself
    auto-advances to status='ready' (so the waiter knows to pick up).
    """
    order_row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order_row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")
    if order_row["cafe_id"] != cafe_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "order belongs to a different cafe")

    item_row = conn.execute(
        "SELECT id, order_id FROM order_items WHERE id = ? AND order_id = ?",
        (item_id, order_id),
    ).fetchone()
    if not item_row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "item not found in this order")

    conn.execute(
        "UPDATE order_items SET status = ? WHERE id = ?",
        (req.status, item_id),
    )

    # Auto-advance the ORDER based on the new mix of item states.
    # Order status moves forward-only — toggling an item back to pending
    # never regresses the order's column.
    items = conn.execute(
        "SELECT status FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchall()
    n = len(items)
    served_count = sum(1 for i in items if i["status"] == "served")
    ready_or_served = sum(1 for i in items if i["status"] in ("ready", "served"))
    any_started = any(i["status"] != "pending" for i in items)

    current_status = order_row["status"]
    target = current_status
    if n > 0 and served_count == n:
        target = "served"
    elif n > 0 and ready_or_served == n:
        target = "ready"
    elif any_started:
        target = "preparing"

    # Forward-only: only auto-advance, never auto-regress
    if STATUS_ORDER.index(target) > STATUS_ORDER.index(current_status):
        new_order_status = target
    else:
        new_order_status = current_status

    if new_order_status != current_status:
        conn.execute(
            "UPDATE orders SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (new_order_status, order_id),
        )
    conn.commit()

    new_row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    order = _hydrate_order(conn, new_row)
    await manager.broadcast(cafe_id, {
        "event": "item_status_changed",
        "order": order.model_dump(),
        "item_id": item_id,
        "item_status": req.status,
    })
    if new_order_status != current_status:
        await manager.broadcast(cafe_id, {"event": "status_changed", "order": order.model_dump()})
    return order
