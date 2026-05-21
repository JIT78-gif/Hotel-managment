"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { getStaffSession } from "@/lib/auth";
import { useStaffWs } from "@/lib/ws";
import type { Order, OrderStatus } from "@/lib/types";

const COLUMNS: { key: OrderStatus; label: string; cls: string; ring: string }[] = [
  { key: "placed",    label: "New",        cls: "border-amber-400",    ring: "ring-amber-200" },
  { key: "preparing", label: "Preparing",  cls: "border-blue-400",     ring: "ring-blue-200" },
  { key: "ready",     label: "Ready",      cls: "border-emerald-400",  ring: "ring-emerald-200" },
  { key: "served",    label: "Served",     cls: "border-stone-300",    ring: "ring-stone-200" },
];

const NEXT: Record<OrderStatus, OrderStatus | null> = {
  placed: "preparing", preparing: "ready", ready: "served", served: null,
};

export default function StaffOrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [token, setToken] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState<OrderStatus>("placed");

  useEffect(() => {
    const s = getStaffSession();
    if (!s) return;
    setToken(s.token);
    api<Order[]>("/staff/orders", { staffToken: s.token }).then(setOrders).catch(e => setErr(e.message));
  }, []);

  const upsert = useCallback((o: Order) => {
    setOrders(prev => {
      const i = prev.findIndex(x => x.id === o.id);
      if (i === -1) return [o, ...prev];
      const copy = [...prev]; copy[i] = { ...copy[i], ...o }; return copy;
    });
  }, []);

  const wsStatus = useStaffWs(token, (m) => {
    if (m.event === "new_order" || m.event === "status_changed") upsert(m.order);
  });

  async function advance(o: Order) {
    const next = NEXT[o.status];
    if (!next) return;
    try {
      const updated = await api<Order>(`/staff/orders/${o.id}`, {
        method: "PATCH", staffToken: token!, json: { status: next },
      });
      upsert(updated);
    } catch (e: any) {
      alert(e.message);
    }
  }

  const byStatus = useMemo(() => {
    const g: Record<OrderStatus, Order[]> = { placed: [], preparing: [], ready: [], served: [] };
    for (const o of orders) g[o.status]?.push(o);
    return g;
  }, [orders]);

  return (
    <div className="px-4 md:px-10 py-6 md:py-8">
      <header className="mb-5 md:mb-8 flex items-center justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] font-medium inline-flex items-center gap-2">
            {wsStatus === "open" ? (
              <span className="inline-flex items-center gap-2 text-terracotta">
                <span className="live-dot" /> Live
              </span>
            ) : (
              <span className="text-amber-700">Connecting…</span>
            )}
          </div>
          <h1 className="display-lg md:text-5xl mt-1">Tonight&apos;s orders</h1>
        </div>
        {err && <div className="text-sm text-red-700">{err}</div>}
      </header>

      {/* Mobile: status tabs + single list */}
      <div className="md:hidden">
        <nav className="flex gap-2 overflow-x-auto no-scrollbar -mx-4 px-4 pb-2 mb-3 snap-strip">
          {COLUMNS.map(c => {
            const count = byStatus[c.key].length;
            const active = tab === c.key;
            return (
              <button key={c.key} onClick={() => setTab(c.key)}
                className={`shrink-0 rounded-full px-4 py-2 text-sm font-medium border whitespace-nowrap transition ${
                  active
                    ? "bg-ink text-cream border-ink"
                    : "bg-cream text-ink border-parchment"
                }`}>
                <span>{c.label}</span>
                {count > 0 && (
                  <span className={`ml-2 tabular-nums text-xs ${active ? "text-terracotta-light" : "text-muted"}`}>
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
        <ul className="space-y-3">
          {byStatus[tab].length === 0 && (
            <li className="text-sm text-muted/70 text-center py-12 italic">Nothing here yet</li>
          )}
          {byStatus[tab].map(o => (
            <OrderCard key={o.id} order={o} onAdvance={advance} />
          ))}
        </ul>
      </div>

      {/* Tablet / desktop: 4-column kanban */}
      <div className="hidden md:grid md:grid-cols-2 xl:grid-cols-4 gap-5">
        {COLUMNS.map(col => (
          <section key={col.key} className={`bg-parchment/40 rounded-2xl p-3 border-t-4 ${col.cls}`}>
            <header className="flex items-center justify-between px-2 py-2 mb-2">
              <h2 className="font-display text-lg">{col.label}</h2>
              <span className="text-xs text-muted tabular-nums">{byStatus[col.key].length}</span>
            </header>
            <ul className="space-y-3 max-h-[70dvh] overflow-y-auto pr-1">
              {byStatus[col.key].length === 0 && (
                <li className="text-sm text-muted/70 text-center py-6 italic">Nothing here yet</li>
              )}
              {byStatus[col.key].map(o => (
                <OrderCard key={o.id} order={o} onAdvance={advance} />
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}

function OrderCard({ order: o, onAdvance }: { order: Order; onAdvance: (o: Order) => void }) {
  const next = NEXT[o.status];
  return (
    <li className="card p-4 animate-fade-up">
      <div className="flex items-baseline justify-between gap-2 mb-2">
        <div className="font-display text-lg">#{o.id} · Table {o.table_number || o.table_id}</div>
        <div className="text-xs text-muted tabular-nums">
          {new Date(o.created_at + "Z").toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>
      <div className="text-xs text-muted mb-3 truncate">{o.customer_name}</div>
      <ul className="text-sm space-y-1 mb-3">
        {o.items.map(it => (
          <li key={it.menu_item_id} className="flex justify-between">
            <span><span className="tabular-nums text-muted mr-2">×{it.quantity}</span>{it.name}</span>
          </li>
        ))}
      </ul>
      <div className="flex items-center justify-between pt-3 border-t border-parchment">
        <span className="tabular-nums font-medium">₹{o.total_amount.toFixed(0)}</span>
        {next && (
          <button onClick={() => onAdvance(o)} className="btn-secondary text-xs py-2 px-3 min-h-[36px]">
            <span className="capitalize">{next}</span> <ArrowRight size={12} />
          </button>
        )}
      </div>
    </li>
  );
}
