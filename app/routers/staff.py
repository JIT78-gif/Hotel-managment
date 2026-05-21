from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import staff_cafe_id
from app.db import get_conn
from app.models import STATUS_ORDER, OrderItemOut, OrderOut, UpdateOrderRequest
from app.realtime import manager

router = APIRouter(prefix="/staff", tags=["staff"])


def _hydrate_order(conn, row) -> OrderOut:
    items = conn.execute(
        "SELECT menu_item_id, name_snapshot, price_snapshot, quantity FROM order_items WHERE order_id = ?",
        (row["id"],),
    ).fetchall()
    table = conn.execute("SELECT table_number FROM tables WHERE id = ?", (row["table_id"],)).fetchone()
    session = conn.execute("SELECT name FROM customer_sessions WHERE token = ?", (row["session_token"],)).fetchone()
    return OrderOut(
        id=row["id"],
        table_id=row["table_id"],
        table_number=table["table_number"] if table else "",
        customer_name=session["name"] if session else "",
        status=row["status"],
        total_amount=row["total_amount"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        items=[
            OrderItemOut(
                menu_item_id=i["menu_item_id"],
                name=i["name_snapshot"],
                price=i["price_snapshot"],
                quantity=i["quantity"],
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
    conn.commit()

    new_row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    order = _hydrate_order(conn, new_row)
    await manager.broadcast(cafe_id, {"event": "status_changed", "order": order.model_dump()})
    return order
