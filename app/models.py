from typing import List, Literal, Optional
from pydantic import BaseModel, Field

OrderStatus = Literal["placed", "preparing", "ready", "served"]
STATUS_ORDER = ["placed", "preparing", "ready", "served"]


class ActivateRequest(BaseModel):
    license_key: str
    admin_email: str = Field(min_length=3, max_length=120)
    admin_password: str = Field(min_length=6, max_length=120)


class ActivateResponse(BaseModel):
    staff_token: str
    cafe_id: int
    cafe_name: str
    role: str = "admin"


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    cafe_id: int
    cafe_name: str
    role: str
    email: str


Role = Literal["admin", "staff"]


class CreateUserRequest(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=120)
    role: Role


class UserOut(BaseModel):
    id: int
    email: str
    role: Role
    created_at: str


class CheckinRequest(BaseModel):
    cafe_id: int
    table_id: Optional[int] = None
    table_number: Optional[str] = Field(default=None, min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=80)
    phone: str = Field(min_length=4, max_length=20)


class CheckinResponse(BaseModel):
    session_token: str
    expires_at: str
    table_id: int
    table_number: str


class MenuItemOut(BaseModel):
    id: int
    name: str
    description: str
    price: float
    image_url: str = ""
    is_available: bool
    category_id: Optional[int] = None


class MenuCategoryOut(BaseModel):
    id: int
    name: str
    sort_order: int
    items: List[MenuItemOut]


class MenuOut(BaseModel):
    categories: List[MenuCategoryOut]
    gst_rate: float = 0
    cafe_name: str = ""


class OrderItemIn(BaseModel):
    menu_item_id: int
    quantity: int = Field(gt=0, le=99)


class PlaceOrderRequest(BaseModel):
    items: List[OrderItemIn] = Field(min_length=1)
    instructions: str = Field(default="", max_length=300)


ItemStatus = Literal["pending", "ready", "served"]


class OrderItemOut(BaseModel):
    menu_item_id: int
    name: str
    price: float
    quantity: int
    status: ItemStatus = "pending"
    item_id: Optional[int] = None  # the order_items row id, used by the per-item PATCH


class OrderOut(BaseModel):
    id: int
    table_id: int
    table_number: str
    customer_name: str
    status: OrderStatus
    total_amount: float
    instructions: str = ""
    gst_rate: float = 0
    gst_amount: float = 0
    created_at: str
    updated_at: str
    items: List[OrderItemOut]


class PlaceOrderResponse(BaseModel):
    order_id: int
    total_amount: float
    gst_amount: float = 0
    grand_total: float = 0
    status: OrderStatus


class UpdateGstRequest(BaseModel):
    gst_rate: float = Field(ge=0, le=28)


class TableSessionInfo(BaseModel):
    name: str
    phone: str
    token: str
    bill_requested: bool
    started_at: str
    party_size: int = 1


class TableBillSummary(BaseModel):
    subtotal: float
    gst_amount: float
    grand_total: float
    order_count: int
    item_count: int


class TableInfo(BaseModel):
    id: int
    table_number: str
    is_occupied: bool
    session: Optional[TableSessionInfo] = None
    bill: Optional[TableBillSummary] = None


class CafeInfo(BaseModel):
    id: int
    name: str
    gst_rate: float


class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=500)


class FeedbackOut(BaseModel):
    id: int
    table_number: str
    customer_name: str
    rating: int
    comment: str
    created_at: str


class UpdateOrderRequest(BaseModel):
    status: OrderStatus


class UpdateOrderItemRequest(BaseModel):
    status: ItemStatus


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    sort_order: int = 0


class CategoryOut(BaseModel):
    id: int
    name: str
    sort_order: int


class MenuItemIn(BaseModel):
    category_id: int
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    price: float = Field(ge=0)
    image_url: str = ""
    is_available: bool = True


class MenuItemUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    image_url: Optional[str] = None
    is_available: Optional[bool] = None


class TableIn(BaseModel):
    table_number: str = Field(min_length=1, max_length=20)


class TableOut(BaseModel):
    id: int
    table_number: str
