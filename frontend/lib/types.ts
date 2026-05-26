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
  gst_rate: number;
  cafe_name: string;
}

export type ItemStatus = "pending" | "ready" | "served";

export interface OrderItem {
  menu_item_id: number;
  name: string;
  price: number;
  quantity: number;
  status?: ItemStatus;
  item_id?: number | null;
}

export interface Order {
  id: number;
  table_id: number;
  table_number: string;
  customer_name: string;
  status: OrderStatus;
  total_amount: number;
  instructions?: string;
  gst_rate?: number;
  gst_amount?: number;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
}

export interface TableSessionInfo {
  name: string;
  phone: string;
  token: string;
  bill_requested: boolean;
  started_at: string;
  party_size?: number;
}

export interface TableBillSummary {
  subtotal: number;
  gst_amount: number;
  grand_total: number;
  order_count: number;
  item_count: number;
}

export interface AdminTable {
  id: number;
  table_number: string;
  is_occupied: boolean;
  session?: TableSessionInfo | null;
  bill?: TableBillSummary | null;
}

export interface CafeInfo {
  id: number;
  name: string;
  gst_rate: number;
}

export interface Feedback {
  id: number;
  table_number: string;
  customer_name: string;
  customer_phone: string;
  rating: number;
  comment: string;
  created_at: string;
}

export interface FeedbackList {
  feedback: Feedback[];
  stats: {
    count: number;
    avg_rating: number | null;
    week_avg_rating: number | null;
  };
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
