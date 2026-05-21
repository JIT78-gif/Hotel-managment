"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { CheckCircle2, Circle, Loader2, PartyPopper, Wifi, WifiOff } from "lucide-react";
import { api } from "@/lib/api";
import { getCustomerSession } from "@/lib/auth";
import { useCustomerWs } from "@/lib/ws";
import type { OrderStatus } from "@/lib/types";

const STAGES: { key: OrderStatus; label: string; copy: string }[] = [
  { key: "placed",    label: "Placed",    copy: "Order received. The kitchen has been notified." },
  { key: "preparing", label: "Preparing", copy: "The kitchen is cooking your dishes." },
  { key: "ready",     label: "Ready",     copy: "Plated and ready. Coming to your table." },
  { key: "served",    label: "Served",    copy: "Bon appétit. Enjoy your meal." },
];

interface OrderView {
  id: number;
  status: OrderStatus;
  total_amount: number;
  created_at?: string;
  items: { menu_item_id: number; name: string; price: number; quantity: number }[];
}

function formatTime(iso: string | undefined): string {
  if (!iso) return "";
  const d = new Date(iso.includes("T") ? iso : iso.replace(" ", "T") + "Z");
  if (isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function OrderStatusPage() {
  const { id } = useParams<{ id: string }>();
  const orderId = Number(id);
  const [order, setOrder] = useState<OrderView | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sessionToken, setSessionToken] = useState<string | null>(null);

  useEffect(() => {
    const s = getCustomerSession();
    if (!s) { setErr("Session expired. Please re-scan the QR."); return; }
    setSessionToken(s.session_token);
    api<OrderView>(`/customer/orders/${orderId}`, { sessionToken: s.session_token })
      .then(setOrder).catch(e => setErr(e.message));
  }, [orderId]);

  const wsStatus = useCustomerWs(sessionToken, (m) => {
    if (m.event === "status_changed" && m.order?.id === orderId) {
      setOrder(o => o ? { ...o, status: m.order.status } : o);
    }
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
  if (!order) return (
    <main className="min-h-dvh grid place-items-center">
      <div className="text-center animate-fade-up">
        <div className="w-10 h-10 rounded-full border-4 border-parchment border-t-terracotta animate-spin mx-auto mb-3" />
        <div className="text-muted text-sm">Loading your order…</div>
      </div>
    </main>
  );

  const isComplete = order.status === "served";
  const currentIdx = STAGES.findIndex(s => s.key === order.status);
  const headerCopy = isComplete ? STAGES[3].copy : STAGES[currentIdx]?.copy;

  return (
    <main className="min-h-dvh pb-12">
      {/* Sticky status pill — always visible while scrolling */}
      <div className="sticky top-0 z-30 bg-cream/95 backdrop-blur-md border-b border-parchment safe-top">
        <div className="px-5 py-3 flex justify-center max-w-2xl mx-auto">
          <StatusPill isComplete={isComplete} wsStatus={wsStatus} />
        </div>
      </div>

      <div className="px-5 md:px-10 py-8 max-w-2xl mx-auto">
        <div className="text-center mb-8 animate-fade-up">
          <h1 className="display-lg">
            Your <em className="text-terracotta">order</em>
          </h1>
          {order.created_at && (
            <div className="text-xs text-muted mt-1 uppercase tracking-[0.18em]">
              Placed at {formatTime(order.created_at)}
            </div>
          )}
          <p className="text-muted mt-3 text-sm max-w-xs mx-auto">{headerCopy}</p>
        </div>

        {/* Progress timeline */}
        <ol className="space-y-3 mb-10">
          {STAGES.map((stage, i) => {
            const done = isComplete || i < currentIdx;
            const active = !isComplete && i === currentIdx;
            return (
              <li key={stage.key} className={`card flex items-center gap-4 p-4 transition ${
                active ? "shadow-warm border-terracotta" : ""
              }`}>
                <span className="shrink-0">
                  {done && <CheckCircle2 className="text-forest" size={28} />}
                  {active && <Loader2 className="text-terracotta animate-spin" size={28} />}
                  {!done && !active && <Circle className="text-muted/40" size={28} />}
                </span>
                <div className="min-w-0">
                  <div className="font-display text-xl">{stage.label}</div>
                  {(done || active) && (
                    <div className="text-sm text-muted leading-snug">{stage.copy}</div>
                  )}
                </div>
              </li>
            );
          })}
        </ol>

        {/* Receipt */}
        <section className="card p-5 md:p-6">
          <h2 className="font-display text-xl mb-4">Order summary</h2>
          <ul className="divide-y divide-parchment">
            {order.items.map(it => (
              <li key={it.menu_item_id} className="flex justify-between py-3 text-sm gap-3">
                <span className="min-w-0">
                  <span className="tabular-nums text-muted mr-2">×{it.quantity}</span>
                  {it.name}
                </span>
                <span className="tabular-nums shrink-0">₹{(it.price * it.quantity).toFixed(0)}</span>
              </li>
            ))}
          </ul>
          <div className="flex justify-between items-baseline pt-4 mt-2 border-t border-parchment">
            <span className="text-muted">Total</span>
            <span className="font-display text-3xl tabular-nums">₹{order.total_amount.toFixed(0)}</span>
          </div>
        </section>

        {isComplete && (
          <div className="mt-6 card p-6 text-center bg-parchment/40 border-forest/20 animate-fade-up">
            <PartyPopper className="mx-auto text-forest mb-2" size={28} />
            <div className="font-display text-2xl">Thank you for dining with us.</div>
            <div className="text-sm text-muted mt-1">Please pay at the table when you&apos;re ready.</div>
          </div>
        )}

        <div className="text-center mt-8">
          <Link href="/customer/menu" className="btn-secondary text-sm">← Add more items</Link>
        </div>
      </div>
    </main>
  );
}

function StatusPill({ isComplete, wsStatus }: { isComplete: boolean; wsStatus: string }) {
  if (isComplete) {
    return (
      <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-forest/10 text-forest text-[11px] uppercase tracking-[0.18em] font-medium">
        <PartyPopper size={12} /> Order complete
      </div>
    );
  }
  if (wsStatus === "open") {
    return (
      <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-terracotta/10 text-terracotta text-[11px] uppercase tracking-[0.18em] font-medium">
        <span className="live-dot" /> Live status
      </div>
    );
  }
  if (wsStatus === "connecting") {
    return (
      <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-parchment text-muted text-[11px] uppercase tracking-[0.18em] font-medium">
        <Wifi size={12} className="animate-pulse" /> Connecting…
      </div>
    );
  }
  return (
    <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-100 text-amber-900 text-[11px] uppercase tracking-[0.18em] font-medium">
      <WifiOff size={12} /> Offline · pull to refresh
    </div>
  );
}
