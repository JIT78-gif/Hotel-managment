"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Wifi, WifiOff, PartyPopper, CheckCircle2, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { getCustomerSession } from "@/lib/auth";
import { useCustomerWs } from "@/lib/ws";
import type { OrderStatus } from "@/lib/types";

const STAGES: { key: OrderStatus; label: string }[] = [
  { key: "placed",    label: "Placed" },
  { key: "preparing", label: "Preparing" },
  { key: "ready",     label: "Ready" },
  { key: "served",    label: "Served" },
];

const STAGE_COPY: Record<OrderStatus, string> = {
  placed:    "Order received. The kitchen has been notified.",
  preparing: "The kitchen is cooking your dishes.",
  ready:     "Plated and ready. Coming to your table.",
  served:    "Bon appétit. Enjoy your meal.",
};

interface OrderView {
  id: number;
  status: OrderStatus;
  total_amount: number;
  created_at: string;
  items: { menu_item_id: number; name: string; price: number; quantity: number }[];
}

function formatTime(iso: string): string {
  // SQLite returns "YYYY-MM-DD HH:MM:SS" in UTC; ensure it's parsed as UTC.
  const d = new Date(iso.includes("T") ? iso : iso.replace(" ", "T") + "Z");
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function MyOrdersPage() {
  const [orders, setOrders] = useState<OrderView[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sessionToken, setSessionToken] = useState<string | null>(null);

  useEffect(() => {
    const s = getCustomerSession();
    if (!s) { setErr("Session expired. Please re-scan the QR."); return; }
    setSessionToken(s.session_token);
    api<OrderView[]>("/customer/orders", { sessionToken: s.session_token })
      .then(setOrders)
      .catch(e => setErr(e.message));
  }, []);

  const wsStatus = useCustomerWs(sessionToken, (m) => {
    if (m.event !== "status_changed" || !m.order) return;
    setOrders(prev => prev
      ? prev.map(o => (o.id === m.order.id ? { ...o, status: m.order.status } : o))
      : prev
    );
  });

  if (err) return (
    <main className="min-h-dvh grid place-items-center px-6 text-center">
      <div className="max-w-sm">
        <h1 className="display-md mb-3">Something went wrong.</h1>
        <p className="text-muted text-sm">{err}</p>
        <Link href="/" className="btn-ghost mt-6 inline-flex">Back to start</Link>
      </div>
    </main>
  );

  if (!orders) return (
    <main className="min-h-dvh grid place-items-center">
      <div className="text-center animate-fade-up">
        <div className="w-10 h-10 rounded-full border-4 border-parchment border-t-terracotta animate-spin mx-auto mb-3" />
        <div className="text-muted text-sm">Loading your orders…</div>
      </div>
    </main>
  );

  const session = getCustomerSession();
  const allServed = orders.length > 0 && orders.every(o => o.status === "served");

  return (
    <main className="min-h-dvh pb-16">
      {/* Sticky header */}
      <div className="sticky top-0 z-30 bg-cream/95 backdrop-blur-md border-b border-parchment safe-top">
        <div className="px-5 py-3 max-w-2xl mx-auto flex items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-[0.18em] text-terracotta font-medium">
              Table {session?.table_number ?? `#${session?.table_id}`}
            </div>
            <div className="font-display text-lg leading-tight">Your orders</div>
          </div>
          <StatusPill wsStatus={wsStatus} allServed={allServed} />
        </div>
      </div>

      <div className="px-5 md:px-8 py-6 max-w-2xl mx-auto space-y-4">
        {orders.length === 0 ? (
          <div className="card p-8 text-center animate-fade-up">
            <div className="font-display text-2xl mb-2">No orders yet.</div>
            <p className="text-muted text-sm mb-5">Open the menu and pick something to start.</p>
            <Link href="/customer/menu" className="btn-primary inline-flex">
              <Plus size={16} /> Browse the menu
            </Link>
          </div>
        ) : (
          orders.map(order => <OrderCard key={order.id} order={order} />)
        )}

        {orders.length > 0 && (
          <div className="pt-2 text-center">
            <Link href="/customer/menu" className="btn-secondary inline-flex">
              <Plus size={16} /> Add more items
            </Link>
          </div>
        )}

        {allServed && (
          <div className="card p-6 text-center bg-parchment/40 border-forest/20 animate-fade-up">
            <PartyPopper className="mx-auto text-forest mb-2" size={28} />
            <div className="font-display text-2xl">Thank you for dining with us.</div>
            <div className="text-sm text-muted mt-1">Please pay at the table when you&apos;re ready.</div>
          </div>
        )}
      </div>
    </main>
  );
}

function OrderCard({ order }: { order: OrderView }) {
  const currentIdx = STAGES.findIndex(s => s.key === order.status);
  const isComplete = order.status === "served";

  return (
    <article className="card p-4 md:p-5 animate-fade-up">
      {/* Header: time + status badge */}
      <header className="flex items-baseline justify-between gap-3 mb-3">
        <div>
          <div className="font-display text-xl">Placed at {formatTime(order.created_at)}</div>
          <div className="text-xs text-muted mt-0.5">{STAGE_COPY[order.status]}</div>
        </div>
        <StatusBadge status={order.status} />
      </header>

      {/* Compact progress dots */}
      <div className="flex items-center gap-1.5 mb-4">
        {STAGES.map((stage, i) => {
          const done = isComplete || i < currentIdx;
          const active = !isComplete && i === currentIdx;
          return (
            <div key={stage.key} className="flex-1 flex flex-col items-center text-center">
              <div className="w-full flex items-center gap-1.5">
                <div className={`flex-1 h-[3px] rounded-full transition ${
                  i === 0 ? "opacity-0" : (done || active ? "bg-terracotta" : "bg-parchment")
                }`} />
                <span className="shrink-0">
                  {done && <CheckCircle2 size={18} className="text-forest" />}
                  {active && <Loader2 size={18} className="text-terracotta animate-spin" />}
                  {!done && !active && (
                    <span className="w-[18px] h-[18px] inline-block rounded-full border-2 border-muted/30" />
                  )}
                </span>
                <div className={`flex-1 h-[3px] rounded-full transition ${
                  i === STAGES.length - 1 ? "opacity-0" : (done ? "bg-terracotta" : "bg-parchment")
                }`} />
              </div>
              <div className={`text-[10px] mt-1 font-medium uppercase tracking-wide ${
                done || active ? "text-ink" : "text-muted/60"
              }`}>
                {stage.label}
              </div>
            </div>
          );
        })}
      </div>

      {/* Items */}
      <ul className="divide-y divide-parchment text-sm">
        {order.items.map(it => (
          <li key={it.menu_item_id} className="flex justify-between py-2 gap-3">
            <span className="min-w-0">
              <span className="tabular-nums text-muted mr-2">×{it.quantity}</span>
              {it.name}
            </span>
            <span className="tabular-nums shrink-0">₹{(it.price * it.quantity).toFixed(0)}</span>
          </li>
        ))}
      </ul>

      <div className="flex justify-between items-baseline pt-3 mt-1 border-t border-parchment">
        <span className="text-muted text-sm">Total</span>
        <span className="font-display text-2xl tabular-nums">₹{order.total_amount.toFixed(0)}</span>
      </div>
    </article>
  );
}

function StatusBadge({ status }: { status: OrderStatus }) {
  const cls: Record<OrderStatus, string> = {
    placed:    "badge-placed",
    preparing: "badge-preparing",
    ready:     "badge-ready",
    served:    "badge-served",
  };
  const label: Record<OrderStatus, string> = {
    placed: "Placed", preparing: "Preparing", ready: "Ready", served: "Served",
  };
  return <span className={`badge ${cls[status]} shrink-0`}>{label[status]}</span>;
}

function StatusPill({ wsStatus, allServed }: { wsStatus: string; allServed: boolean }) {
  if (allServed) {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-forest/10 text-forest text-[10px] uppercase tracking-[0.18em] font-medium">
        <PartyPopper size={12} /> Complete
      </div>
    );
  }
  if (wsStatus === "open") {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-terracotta/10 text-terracotta text-[10px] uppercase tracking-[0.18em] font-medium">
        <span className="live-dot" /> Live
      </div>
    );
  }
  if (wsStatus === "connecting" || wsStatus === "closed") {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-parchment text-muted text-[10px] uppercase tracking-[0.18em] font-medium">
        <Wifi size={12} className="animate-pulse" /> Connecting
      </div>
    );
  }
  return (
    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-100 text-amber-900 text-[10px] uppercase tracking-[0.18em] font-medium">
      <WifiOff size={12} /> Offline
    </div>
  );
}
