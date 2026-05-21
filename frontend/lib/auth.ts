// Client-side auth helpers using cookies (so middleware can read them server-side too).
// Customer session lives in localStorage (not visible to middleware; customer routes are unguarded).
import type { LoginResponse, Role } from "./types";

const STAFF_COOKIE = "hc_staff";
const CUSTOMER_KEY = "hc_session";

export function saveStaffSession(login: LoginResponse) {
  if (typeof document === "undefined") return;
  const value = encodeURIComponent(JSON.stringify(login));
  // 30-day cookie; SameSite=Lax so middleware sees it on same-origin nav
  document.cookie = `${STAFF_COOKIE}=${value}; path=/; max-age=${60 * 60 * 24 * 30}; SameSite=Lax`;
}

export function getStaffSession(): LoginResponse | null {
  if (typeof document === "undefined") return null;
  const cookies = document.cookie.split("; ").filter(Boolean);
  for (const c of cookies) {
    const [k, ...rest] = c.split("=");
    if (k === STAFF_COOKIE) {
      try { return JSON.parse(decodeURIComponent(rest.join("="))); } catch { return null; }
    }
  }
  return null;
}

export function logoutStaff() {
  if (typeof document === "undefined") return;
  document.cookie = `${STAFF_COOKIE}=; path=/; max-age=0`;
}

export interface CustomerSession {
  session_token: string;
  cafe_id: number;
  table_id: number;
  table_number: string;
  name: string;
  expires_at: string;
}

export function saveCustomerSession(s: CustomerSession) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(CUSTOMER_KEY, JSON.stringify(s));
}

export function getCustomerSession(): CustomerSession | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(CUSTOMER_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

export function clearCustomerSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(CUSTOMER_KEY);
}

export function roleCanAccess(role: Role | null | undefined, path: string): boolean {
  if (!role) return false;
  if (path.startsWith("/admin")) return role === "admin";
  if (path.startsWith("/staff")) return role === "admin" || role === "staff";
  return true;
}
