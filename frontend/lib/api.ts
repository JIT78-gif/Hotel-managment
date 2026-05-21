// The Next.js rewrite (next.config.mjs) proxies /api/* → http://localhost:8000/*
// So from the client we can always call relative paths.
const BASE = "/api";

interface RequestOpts extends RequestInit {
  staffToken?: string;
  sessionToken?: string;
  json?: any;
}

export async function api<T = any>(path: string, opts: RequestOpts = {}): Promise<T> {
  const { staffToken, sessionToken, json, headers, ...rest } = opts;
  const h: Record<string, string> = { ...(headers as any) };
  if (json !== undefined) h["Content-Type"] = "application/json";
  if (staffToken) h["Authorization"] = `Bearer ${staffToken}`;
  if (sessionToken) h["X-Session-Token"] = sessionToken;

  const res = await fetch(`${BASE}${path}`, {
    ...rest,
    headers: h,
    body: json !== undefined ? JSON.stringify(json) : (rest.body as any),
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {}
    const err = new Error(`${res.status} ${detail}`) as any;
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return undefined as any;
  return res.json();
}

export function wsUrl(path: string): string {
  if (typeof window === "undefined") return "";
  // Explicit override (used when backend has its own public domain, e.g. wss://api.example.com)
  const override = process.env.NEXT_PUBLIC_BACKEND_WS_URL;
  if (override) {
    return `${override.replace(/\/$/, "")}${path}`;
  }
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  // Local dev: backend listens on a separate port on localhost
  if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    const port = process.env.NEXT_PUBLIC_BACKEND_PORT || "8000";
    return `${proto}://${window.location.hostname}:${port}${path}`;
  }
  // Production default: reverse proxy (EasyPanel / Caddy / Traefik) routes /ws/* to the backend
  return `${proto}://${window.location.host}${path}`;
}
