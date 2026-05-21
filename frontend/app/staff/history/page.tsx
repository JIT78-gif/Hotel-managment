"use client";
import { useEffect, useMemo, useState } from "react";
import { TrendingUp, Calendar, IndianRupee, ShoppingBag } from "lucide-react";
import { api } from "@/lib/api";
import { getStaffSession } from "@/lib/auth";
import type { Order, OrderStatus } from "@/lib/types";

type Period = "today" | "week" | "month" | "all";

const TABS: { key: Period; label: string }[] = [
  { key: "today", label: "Today" },
  { key: "week",  label: "This week" },
  { key: "month", label: "This month" },
  { key: "all",   label: "All" },
];

const STATUS_BADGE: Record<OrderStatus, string> = {
  placed: "badge-placed",
  preparing: "badge-preparing",
  ready: "badge-ready",
  served: "badge-served",
};

function parseUtc(iso: string): Date {
  return new Date(iso.includes("T") ? iso : iso.replace(" ", "T") + "Z");
}

function timeOf(iso: string): string {
  const d = parseUtc(iso);
  return isNaN(d.getTime()) ? "" : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function dateKey(iso: string): string {
  // Local YYYY-MM-DD for grouping
  const d = parseUtc(iso);
  if (isNaN(d.getTime())) return iso;
  const y = d.getFullYear(), m = String(d.getMonth() + 1).padStart(2, "0"), day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function prettyDate(key: string): string {
  const [y, m, d] = key.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const yest  = new Date(today); yest.setDate(yest.getDate() - 1);
  if (dt.getTime() === today.getTime()) return "Today";
  if (dt.getTime() === yest.getTime()) return "Yesterday";
  return dt.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
}

export default function StaffHistoryPage() {
  const [token, setToken] = useState<string | null>(null);
  const [tab, setTab] = useState<Period>("today");
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // Stat cards always reflect today + week, regardless of which tab is active.
  const [stats, setStats] = useState({
    todayCount: 0, todayRevenue: 0, weekRevenue: 0,
  });

  useEffect(() => {
    const s = getStaffSession();
    if (!s) return;
    setToken(s.token);
    // Load stats in parallel with the visible tab
    Promise.all([
      api<Order[]>("/staff/orders?period=today", { staffToken: s.token }),
      api<Order[]>("/staff/orders?period=week",  { staffToken: s.token }),
    ]).then(([today, week]) => {
      setStats({
        todayCount: today.length,
        todayRevenue: today.reduce((sum, o) => sum + o.total_amount, 0),
        weekRevenue:  week.reduce((sum, o) => sum + o.total_amount, 0),
      });
    }).catch(e => setErr(e.message));
  }, []);

  useEffect(() => {
    if (!token) return;
    setLoading(true); setErr(null);
    api<Order[]>(`/staff/orders?period=${tab}`, { staffToken: token })
      .then(setOrders)
      .catch(e => setErr(e.message))
      .finally(() => setLoading(false));
  }, [tab, token]);

  // Group orders by local date
  const grouped = useMemo(() => {
    const buckets: Record<string, Order[]> = {};
    for (const o of orders) {
      const k = dateKey(o.created_at);
      (buckets[k] ||= []).push(o);
    }
    return Object.entries(buckets).sort((a, b) => (a[0] < b[0] ? 1 : -1));
  }, [orders]);

  const tabTotal = useMemo(
    () => orders.reduce((sum, o) => sum + o.total_amount, 0),
    [orders]
  );

  return (
    <div className="px-4 md:px-10 py-6 md:py-8">
      <header className="mb-6 md:mb-8">
        <span className="eyebrow">Operations</span>
        <h1 className="display-lg mt-2">History.</h1>
        <p className="text-muted mt-1 text-sm">Every order placed at your cafe.</p>
      </header>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        <StatCard
          icon={<ShoppingBag size={16} />}
          label="Today's orders"
          value={stats.todayCount.toString()}
        />
        <StatCard
          icon={<IndianRupee size={16} />}
          label="Today's revenue"
          value={`₹${stats.todayRevenue.toFixed(0)}`}
        />
        <StatCard
          icon={<TrendingUp size={16} />}
          label="This week's revenue"
          value={`₹${stats.weekRevenue.toFixed(0)}`}
          className="col-span-2 md:col-span-1"
        />
      </div>

      {/* Tabs */}
      <nav className="flex gap-2 overflow-x-auto no-scrollbar -mx-4 px-4 md:mx-0 md:px-0 mb-4 snap-strip">
        {TABS.map(t => {
          const active = tab === t.key;
          return (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`shrink-0 rounded-full px-4 py-2 text-sm font-medium border whitespace-nowrap transition ${
                active ? "bg-ink text-cream border-ink" : "bg-cream text-ink border-parchment"
              }`}>
              {t.label}
            </button>
          );
        })}
        <div className="ml-auto shrink-0 self-center text-xs text-muted whitespace-nowrap pr-1">
          {orders.length} orders · ₹{tabTotal.toFixed(0)}
        </div>
      </nav>

      {err && (
        <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {err}
        </div>
      )}

      {loading ? (
        <div className="py-16 text-center text-muted text-sm">Loading…</div>
      ) : orders.length === 0 ? (
        <div className="card p-10 text-center text-muted">
          <Calendar size={28} className="mx-auto mb-3 text-muted/50" />
          <div className="font-display text-xl">Nothing here yet.</div>
          <p className="text-sm mt-1">No orders match this period.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {grouped.map(([day, dayOrders]) => {
            const dayRev = dayOrders.reduce((s, o) => s + o.total_amount, 0);
            return (
              <section key={day}>
                <header className="flex items-baseline justify-between mb-2 px-1">
                  <h2 className="font-display text-lg">{prettyDate(day)}</h2>
                  <div className="text-xs text-muted">
                    {dayOrders.length} orders · <span className="tabular-nums">₹{dayRev.toFixed(0)}</span>
                  </div>
                </header>
                <ul className="space-y-2">
                  {dayOrders.map(o => (
                    <li key={o.id} className="card p-3 md:p-4 flex items-center gap-3">
                      <div className="text-xs text-muted tabular-nums w-14 shrink-0">{timeOf(o.created_at)}</div>
                      <div className="font-display text-sm shrink-0 w-12">#{o.id}</div>
                      <div className="text-xs text-muted hidden sm:block shrink-0 w-20">Table {o.table_number || o.table_id}</div>
                      <div className="flex-1 min-w-0 text-sm truncate">
                        {o.items.map(it => `${it.quantity}× ${it.name}`).join(", ")}
                      </div>
                      <div className="text-right shrink-0">
                        <div className="tabular-nums font-medium text-sm">₹{o.total_amount.toFixed(0)}</div>
                        <span className={`badge text-[10px] mt-1 ${STATUS_BADGE[o.status]}`}>{o.status}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

function StatCard({ icon, label, value, className = "" }: {
  icon: React.ReactNode; label: string; value: string; className?: string;
}) {
  return (
    <div className={`card p-4 ${className}`}>
      <div className="text-[11px] uppercase tracking-[0.14em] text-muted flex items-center gap-2 mb-2">
        {icon} {label}
      </div>
      <div className="font-display text-3xl tabular-nums">{value}</div>
    </div>
  );
}
