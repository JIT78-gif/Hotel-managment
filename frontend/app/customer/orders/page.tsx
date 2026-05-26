"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Plus, Wifi, WifiOff, PartyPopper, CheckCircle2, Loader2, Receipt, Hand, PackageCheck, Star } from "lucide-react";
import { api } from "@/lib/api";
import { clearCustomerSession, getCustomerSession } from "@/lib/auth";
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
  gst_rate?: number;
  gst_amount?: number;
  grand_total?: number;
  instructions?: string;
  created_at: string;
  items: {
    item_id?: number;
    menu_item_id: number;
    name: string;
    price: number;
    quantity: number;
    status?: "pending" | "ready" | "served";
  }[];
}

interface OrdersResponse {
  session: { bill_requested: boolean; paid: boolean };
  table?: { unserved_count: number; others_unserved_count: number };
  orders: OrderView[];
}

function formatTime(iso: string): string {
  const d = new Date(iso.includes("T") ? iso : iso.replace(" ", "T") + "Z");
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function MyOrdersPage() {
  const [data, setData] = useState<OrdersResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [requesting, setRequesting] = useState(false);
  const [paidOverlay, setPaidOverlay] = useState(false);

  useEffect(() => {
    const s = getCustomerSession();
    if (!s) { setErr("Session expired. Please re-scan the QR."); return; }
    setSessionToken(s.session_token);
    api<OrdersResponse>("/customer/orders", { sessionToken: s.session_token })
      .then(setData)
      .catch(e => setErr(e.message));
  }, []);

  const wsStatus = useCustomerWs(sessionToken, (m) => {
    if ((m.event === "status_changed" || m.event === "item_status_changed") && m.order) {
      setData(prev => prev
        ? {
            ...prev,
            orders: prev.orders.map(o => o.id === m.order.id
              ? { ...o, status: m.order.status, items: m.order.items ?? o.items }
              : o),
          }
        : prev
      );
    }
    if (m.event === "table_paid") {
      // Admin closed the bill — clean up local session and show the "thank you" overlay
      setPaidOverlay(true);
      clearCustomerSession();
    }
  });

  async function requestBill() {
    if (!sessionToken) return;
    setRequesting(true); setErr(null);
    try {
      await api("/customer/request_bill", { method: "POST", sessionToken });
      setData(prev => prev ? { ...prev, session: { ...prev.session, bill_requested: true } } : prev);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setRequesting(false);
    }
  }

  // Aggregate the combined bill across all orders in this dining session
  const bill = useMemo(() => {
    if (!data) return { subtotal: 0, gst: 0, grand: 0, gstRate: 0 };
    const subtotal = data.orders.reduce((s, o) => s + o.total_amount, 0);
    const gst = data.orders.reduce((s, o) => s + (o.gst_amount ?? 0), 0);
    const gstRate = data.orders[0]?.gst_rate ?? 0;
    return { subtotal, gst, grand: subtotal + gst, gstRate };
  }, [data]);

  if (paidOverlay) return <ThankYouScreen sessionToken={sessionToken} />;

  // Full-screen error ONLY when we couldn't load any data at all.
  // Action errors (e.g. request_bill 409) are shown inline as a banner so
  // the customer doesn't lose their place.
  if (err && !data) return (
    <main className="min-h-dvh grid place-items-center px-6 text-center">
      <div className="max-w-sm">
        <h1 className="display-md mb-3">Something went wrong.</h1>
        <p className="text-muted text-sm">{err}</p>
        <Link href="/customer/menu" className="btn-primary mt-6 inline-flex">Back to menu</Link>
      </div>
    </main>
  );

  if (!data) return (
    <main className="min-h-dvh grid place-items-center">
      <div className="text-center animate-fade-up">
        <div className="w-10 h-10 rounded-full border-4 border-parchment border-t-terracotta animate-spin mx-auto mb-3" />
        <div className="text-muted text-sm">Loading your orders…</div>
      </div>
    </main>
  );

  const session = getCustomerSession();
  // Hard gate: every line item AT THIS TABLE (across every diner) must be
  // 'served' before we unlock the request-bill button. The backend enforces
  // the same rule — we mirror its `table.unserved_count` here so the customer
  // doesn't see "all served" while the request-bill 409s on another diner's
  // pending item.
  const myUnserved = data.orders.reduce(
    (n, o) => n + o.items.filter(i => i.status !== "served").length,
    0
  );
  const tableUnserved = data.table?.unserved_count ?? myUnserved;
  const othersUnserved = data.table?.others_unserved_count ?? 0;
  const allServed = data.orders.length > 0 && tableUnserved === 0;
  const billRequested = data.session.bill_requested;

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
          <StatusPill wsStatus={wsStatus} billRequested={billRequested} allServed={allServed} />
        </div>
      </div>

      <div className="px-5 md:px-8 py-6 max-w-2xl mx-auto space-y-4">
        {err && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 flex items-start justify-between gap-3 animate-fade-up">
            <span className="flex-1">{err}</span>
            <button
              type="button"
              onClick={() => setErr(null)}
              className="text-xs uppercase tracking-wide text-red-700 underline shrink-0"
            >
              Dismiss
            </button>
          </div>
        )}
        {data.orders.length === 0 ? (
          <div className="card p-8 text-center animate-fade-up">
            <div className="font-display text-2xl mb-2">No orders yet.</div>
            <p className="text-muted text-sm mb-5">Open the menu and pick something to start.</p>
            <Link href="/customer/menu" className="btn-primary inline-flex">
              <Plus size={16} /> Browse the menu
            </Link>
          </div>
        ) : (
          <>
            {/* Combined bill across the whole dining session */}
            <section className="card p-5 bg-parchment/30">
              <header className="flex items-center justify-between mb-3">
                <h2 className="font-display text-xl flex items-center gap-2">
                  <Receipt size={18} className="text-terracotta" /> Your bill
                </h2>
                <span className="text-[11px] text-muted">{data.orders.length} order{data.orders.length === 1 ? "" : "s"}</span>
              </header>
              <dl className="space-y-1 text-sm">
                <div className="flex justify-between text-muted">
                  <dt>Subtotal</dt>
                  <dd className="tabular-nums">₹{bill.subtotal.toFixed(0)}</dd>
                </div>
                {bill.gstRate > 0 && (
                  <div className="flex justify-between text-muted">
                    <dt>GST ({bill.gstRate % 1 === 0 ? bill.gstRate.toFixed(0) : bill.gstRate.toFixed(1)}%)</dt>
                    <dd className="tabular-nums">₹{bill.gst.toFixed(0)}</dd>
                  </div>
                )}
                <div className="flex justify-between items-baseline pt-2 border-t border-parchment">
                  <dt className="font-medium">Grand total</dt>
                  <dd className="font-display text-3xl tabular-nums">₹{bill.grand.toFixed(0)}</dd>
                </div>
              </dl>
            </section>

            {data.orders.map(order => <OrderCard key={order.id} order={order} />)}

            <div className="pt-2 text-center">
              <Link href="/customer/menu" className="btn-secondary inline-flex">
                <Plus size={16} /> Add more items
              </Link>
            </div>

            {/* Request bill / waiting / complete */}
            <section className="pt-2">
              {billRequested ? (
                <div className="card p-5 text-center bg-amber-50 border-amber-200 animate-fade-up">
                  <Hand className="mx-auto text-amber-700 mb-2" size={24} />
                  <div className="font-display text-xl text-amber-900">Waiting for staff…</div>
                  <p className="text-sm text-amber-900/70 mt-1">
                    Please pay at the counter when you&apos;re ready. We&apos;ll show a thank-you screen once payment is confirmed.
                  </p>
                </div>
              ) : allServed ? (
                <button
                  onClick={requestBill}
                  disabled={requesting}
                  className="btn-primary w-full text-base h-14"
                >
                  <Hand size={18} /> {requesting ? "Calling staff…" : "I'm done — please bring the bill"}
                </button>
              ) : (
                <div className="card p-4 text-center bg-parchment/50 border-parchment">
                  <div className="text-sm text-muted">
                    {myUnserved > 0
                      ? (myUnserved === 1 ? "1 item still on the way" : `${myUnserved} items still on the way`)
                      : othersUnserved === 1
                        ? "Your items have arrived — someone else at your table is still waiting on 1 item"
                        : `Your items have arrived — someone else at your table is still waiting on ${othersUnserved} items`
                    }
                    {" · "}
                    <span className="text-[11px]">you&apos;ll be able to ask for the bill once everything arrives</span>
                  </div>
                </div>
              )}
            </section>
          </>
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
      <header className="flex items-baseline justify-between gap-3 mb-3">
        <div>
          <div className="font-display text-xl">Placed at {formatTime(order.created_at)}</div>
          <div className="text-xs text-muted mt-0.5">{STAGE_COPY[order.status]}</div>
        </div>
        <StatusBadge status={order.status} />
      </header>

      {/* Progress dots */}
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
        {order.items.map(it => {
          const ready = it.status === "ready";
          const served = it.status === "served";
          return (
            <li key={it.item_id ?? it.menu_item_id} className="flex justify-between py-2 gap-3 items-center">
              <span className="min-w-0 flex items-center gap-2 flex-wrap">
                <span className={`shrink-0 w-4 h-4 rounded-full grid place-items-center transition ${
                  served || ready ? "bg-forest text-cream" : "bg-parchment"
                }`} aria-hidden>
                  {served && <PackageCheck size={12} strokeWidth={2.5} />}
                  {ready && <CheckCircle2 size={14} strokeWidth={3} />}
                </span>
                <span className="tabular-nums text-muted">×{it.quantity}</span>
                <span className={served ? "text-forest font-medium" : ready ? "text-forest" : ""}>{it.name}</span>
                {served && (
                  <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wide text-forest font-medium bg-forest/10 rounded-full px-2 py-0.5">
                    <PackageCheck size={10} strokeWidth={2.5} /> arrived
                  </span>
                )}
                {ready && (
                  <span className="text-[10px] uppercase tracking-wide text-forest font-medium">ready</span>
                )}
              </span>
              <span className="tabular-nums shrink-0">₹{(it.price * it.quantity).toFixed(0)}</span>
            </li>
          );
        })}
      </ul>

      {order.instructions && (
        <div className="mt-2 text-sm italic text-terracotta-dark bg-terracotta/5 border border-terracotta/15 rounded-lg px-3 py-2">
          “{order.instructions}”
        </div>
      )}

      <div className="flex justify-between items-baseline pt-3 mt-1 border-t border-parchment text-sm">
        <span className="text-muted">Order total</span>
        <span className="tabular-nums">
          ₹{order.total_amount.toFixed(0)}
          {(order.gst_amount ?? 0) > 0 && (
            <span className="text-muted/60 ml-1">+ ₹{(order.gst_amount ?? 0).toFixed(0)} GST</span>
          )}
        </span>
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

function StatusPill({ wsStatus, billRequested, allServed }: {
  wsStatus: string; billRequested: boolean; allServed: boolean;
}) {
  if (billRequested) {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-100 text-amber-900 text-[10px] uppercase tracking-[0.18em] font-medium">
        <Hand size={12} /> Bill requested
      </div>
    );
  }
  if (allServed) {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-forest/10 text-forest text-[10px] uppercase tracking-[0.18em] font-medium">
        <PartyPopper size={12} /> All served
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

function ThankYouScreen({ sessionToken }: { sessionToken: string | null }) {
  const [rating, setRating] = useState<number>(0);
  const [hover, setHover] = useState<number>(0);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    if (!sessionToken || rating < 1) return;
    setBusy(true); setErr(null);
    try {
      await api("/customer/feedback", {
        method: "POST", sessionToken,
        json: { rating, comment: comment.trim() },
      });
      setSubmitted(true);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (submitted) return <FinalThanks message="Thanks for the feedback. See you again." />;

  return (
    <main className="min-h-dvh grid place-items-center px-6 py-10 text-center">
      <div className="max-w-md w-full animate-fade-up">
        <PartyPopper className="mx-auto text-forest mb-3" size={40} />
        <h1 className="display-md mb-2">
          Thank you<span className="text-terracotta">.</span>
        </h1>
        <p className="text-muted leading-relaxed mb-6 text-sm">
          Payment received. How was your meal?
        </p>

        {/* Star picker */}
        <div className="flex items-center justify-center gap-1 mb-5"
             onMouseLeave={() => setHover(0)}>
          {[1, 2, 3, 4, 5].map(n => {
            const filled = (hover || rating) >= n;
            return (
              <button
                key={n}
                type="button"
                onClick={() => setRating(n)}
                onMouseEnter={() => setHover(n)}
                aria-label={`${n} star${n === 1 ? "" : "s"}`}
                className="p-1 transition active:scale-90"
              >
                <Star
                  size={36}
                  strokeWidth={1.5}
                  className={filled ? "text-terracotta fill-terracotta" : "text-muted/40"}
                />
              </button>
            );
          })}
        </div>
        {rating > 0 && (
          <div className="text-xs uppercase tracking-[0.18em] text-terracotta font-medium mb-4">
            {["", "Could be better", "Okay", "Good", "Great", "Loved it"][rating]}
          </div>
        )}

        <textarea
          value={comment}
          onChange={e => setComment(e.target.value)}
          maxLength={500}
          rows={3}
          placeholder="Anything you'd like to share? (optional)"
          className="input text-sm w-full mb-3 resize-none"
        />

        {err && <div className="text-sm text-red-700 mb-3">{err}</div>}

        <div className="flex gap-2">
          <button
            onClick={() => setSubmitted(true)}
            className="btn-ghost flex-1"
            disabled={busy}
          >
            Skip
          </button>
          <button
            onClick={submit}
            disabled={busy || rating < 1}
            className="btn-primary flex-1"
          >
            {busy ? "Sending…" : "Submit feedback"}
          </button>
        </div>
      </div>
    </main>
  );
}

function FinalThanks({ message }: { message: string }) {
  return (
    <main className="min-h-dvh grid place-items-center px-6 text-center">
      <div className="max-w-md animate-fade-up">
        <PartyPopper className="mx-auto text-forest mb-4" size={48} />
        <h1 className="display-lg mb-3">
          Thank you<span className="text-terracotta">.</span>
        </h1>
        <p className="text-muted leading-relaxed mb-8">{message}</p>
        <Link href="/" className="btn-primary inline-flex">Back to start</Link>
      </div>
    </main>
  );
}
