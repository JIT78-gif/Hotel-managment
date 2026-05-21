import sqlite3
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app import auth as auth_mod
from app.auth import admin_cafe_id as staff_cafe_id  # admin-only for /admin/*
from app.db import get_conn
from app.models import (
    CategoryIn, CategoryOut, CreateUserRequest, MenuItemIn, MenuItemOut,
    MenuItemUpdate, TableIn, TableOut, UserOut,
)

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
@router.get("/tables", response_model=List[TableOut])
def list_tables(cafe_id: int = Depends(staff_cafe_id), conn=Depends(get_conn)):
    rows = conn.execute(
        "SELECT id, table_number FROM tables WHERE cafe_id = ? ORDER BY id",
        (cafe_id,),
    ).fetchall()
    return [TableOut(id=r["id"], table_number=r["table_number"]) for r in rows]


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
