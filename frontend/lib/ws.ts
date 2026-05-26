"use client";
import { useEffect, useRef, useState } from "react";
import { wsUrl } from "./api";

export type WsStatus = "idle" | "connecting" | "open" | "closed" | "error";
// Server broadcasts include arbitrary payload keys depending on event type
// (new_order/status_changed → order; bill_requested/table_paid → table).
type Msg = { event: string; [key: string]: any };

/**
 * WS hook with a callback ref (always invokes latest onMessage) and
 * auto-reconnect with exponential backoff (1s → 2s → 4s → 8s, capped at 10s).
 * Reconnect attempts continue indefinitely while the component is mounted,
 * so a backend hot-reload doesn't leave the customer permanently offline.
 */
function useWs(path: string | null, onMessage: (m: Msg) => void): WsStatus {
  const cbRef = useRef(onMessage);
  cbRef.current = onMessage;
  const [status, setStatus] = useState<WsStatus>("idle");

  useEffect(() => {
    if (!path) {
      setStatus("idle");
      return;
    }
    let cancelled = false;
    let attempt = 0;
    let ws: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (cancelled) return;
      const url = wsUrl(path);
      // eslint-disable-next-line no-console
      console.log(`[ws] connecting (attempt ${attempt + 1}):`, url);
      setStatus("connecting");
      ws = new WebSocket(url);

      ws.onopen = () => {
        if (cancelled) return;
        attempt = 0;
        setStatus("open");
        // eslint-disable-next-line no-console
        console.log("[ws] open:", url);
      };
      ws.onmessage = (evt) => {
        // eslint-disable-next-line no-console
        console.log("[ws] message:", evt.data);
        try { cbRef.current(JSON.parse(evt.data)); } catch (e) {
          // eslint-disable-next-line no-console
          console.warn("[ws] bad payload:", evt.data, e);
        }
      };
      ws.onerror = (e) => {
        if (cancelled) return;
        // eslint-disable-next-line no-console
        console.warn("[ws] error:", e);
      };
      ws.onclose = (e) => {
        if (cancelled) return;
        // eslint-disable-next-line no-console
        console.log("[ws] closed:", e.code, e.reason);
        // 4401 = our backend's "auth rejected" code. Don't retry — token is bad.
        if (e.code === 4401) {
          setStatus("error");
          return;
        }
        setStatus("closed");
        const delayMs = Math.min(10_000, 1_000 * Math.pow(2, attempt));
        attempt += 1;
        retryTimer = setTimeout(connect, delayMs);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      try { ws?.close(); } catch {}
    };
  }, [path]);

  return status;
}

export function useStaffWs(staffToken: string | null | undefined, onMessage: (m: Msg) => void) {
  const path = staffToken ? `/ws/staff?token=${encodeURIComponent(staffToken)}` : null;
  return useWs(path, onMessage);
}

export function useCustomerWs(sessionToken: string | null | undefined, onMessage: (m: Msg) => void) {
  const path = sessionToken ? `/ws/customer?session_token=${encodeURIComponent(sessionToken)}` : null;
  return useWs(path, onMessage);
}
