export type Role = "admin" | "staff";
export type OrderStatus = "placed" | "preparing" | "ready" | "served";

export interface MenuItem {
  id: number;
  name: string;
  description: string;
  price: number;
  image_url: string;
  is_available: boolean;
  category_id?: number | null;
}

export interface MenuCategory {
  id: number;
  name: string;
  sort_order: number;
  items: MenuItem[];
}

export interface Menu {
  categories: MenuCategory[];
}

export interface OrderItem {
  menu_item_id: number;
  name: string;
  price: number;
  quantity: number;
}

export interface Order {
  id: number;
  table_id: number;
  table_number: string;
  customer_name: string;
  status: OrderStatus;
  total_amount: number;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
}

export interface LoginResponse {
  token: string;
  cafe_id: number;
  cafe_name: string;
  role: Role;
  email: string;
}

export interface UserOut {
  id: number;
  email: string;
  role: Role;
  created_at: string;
}
