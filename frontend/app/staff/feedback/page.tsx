"use client";
import { useEffect, useState } from "react";
import { Star, MessageSquare } from "lucide-react";
import { api } from "@/lib/api";
import { getStaffSession } from "@/lib/auth";
import type { FeedbackList } from "@/lib/types";

type Period = "today" | "week" | "month" | "all";

const TABS: { key: Period; label: string }[] = [
  { key: "today", label: "Today" },
  { key: "week",  label: "This week" },
  { key: "month", label: "This month" },
  { key: "all",   label: "All" },
];

function StarRow({ value, size = 14 }: { value: number; size?: number }) {
  return (
    <span className="inline-flex items-center gap-0.5" aria-label={`${value} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map(n => (
        <Star
          key={n}
          size={size}
          strokeWidth={1.5}
          className={n <= value ? "text-terracotta fill-terracotta" : "text-muted/30"}
        />
      ))}
    </span>
  );
}

function timeOf(iso: string): string {
  const d = new Date(iso.includes("T") ? iso : iso.replace(" ", "T") + "Z");
  if (isNaN(d.getTime())) return iso;
  const now = Date.now();
  const diffMin = Math.round((now - d.getTime()) / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin} min ago`;
  if (diffMin < 60 * 24) return `${Math.floor(diffMin / 60)}h ago`;
  return d.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function FeedbackPage() {
  const [token, setToken] = useState<string | null>(null);
  const [tab, setTab] = useState<Period>("all");
  const [data, setData] = useState<FeedbackList | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const s = getStaffSession();
    if (!s) return;
    setToken(s.token);
  }, []);

  useEffect(() => {
    if (!token) return;
    setLoading(true); setErr(null);
    api<FeedbackList>(`/admin/feedback?period=${tab}`, { staffToken: token })
      .then(setData)
      .catch(e => setErr(e.message))
      .finally(() => setLoading(false));
  }, [token, tab]);

  return (
    <div className="px-3 sm:px-5 md:px-10 py-4 sm:py-6 md:py-8">
      <header className="mb-4 sm:mb-6 md:mb-8">
        <span className="eyebrow">Customer voice</span>
        <h1 className="font-display text-3xl sm:text-4xl md:text-5xl leading-[1.05] tracking-tight mt-2">Feedback.</h1>
        <p className="text-muted mt-1 text-xs sm:text-sm">Real ratings + comments left by your guests after they paid.</p>
      </header>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-3 mb-4 sm:mb-6">
        <Stat
          label="Total reviews"
          value={(data?.stats.count ?? 0).toString()}
        />
        <Stat
          label={`${tab === "all" ? "All-time" : "Period"} average`}
          value={data?.stats.avg_rating != null ? `${data.stats.avg_rating.toFixed(1)} ★` : "—"}
        />
        <Stat
          label="This week"
          value={data?.stats.week_avg_rating != null ? `${data.stats.week_avg_rating.toFixed(1)} ★` : "—"}
          className="col-span-2 sm:col-span-1"
        />
      </div>

      {/* Tabs */}
      <nav className="flex gap-2 overflow-x-auto no-scrollbar -mx-3 px-3 sm:mx-0 sm:px-0 mb-4 snap-strip">
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
      </nav>

      {err && (
        <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {err}
        </div>
      )}

      {loading ? (
        <div className="py-16 text-center text-muted text-sm">Loading…</div>
      ) : !data || data.feedback.length === 0 ? (
        <div className="card p-10 text-center text-muted">
          <MessageSquare size={28} className="mx-auto mb-3 text-muted/50" />
          <div className="font-display text-xl">No feedback yet.</div>
          <p className="text-sm mt-1">Feedback shows up here when customers rate after paying.</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {data.feedback.map(f => (
            <li key={f.id} className="card p-4">
              <header className="flex items-start justify-between gap-3 mb-2">
                <div className="min-w-0">
                  <div className="font-display text-lg leading-tight truncate">{f.customer_name}</div>
                  <div className="text-[11px] text-muted">
                    Table {f.table_number} · {timeOf(f.created_at)}
                  </div>
                </div>
                <StarRow value={f.rating} size={16} />
              </header>
              {f.comment && (
                <p className="text-sm text-ink leading-relaxed italic">
                  &ldquo;{f.comment}&rdquo;
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Stat({ label, value, className = "" }: {
  label: string; value: string; className?: string;
}) {
  return (
    <div className={`card p-3 sm:p-4 ${className}`}>
      <div className="text-[10px] sm:text-[11px] uppercase tracking-[0.12em] sm:tracking-[0.14em] text-muted mb-0.5 sm:mb-1 truncate">{label}</div>
      <div className="font-display text-xl sm:text-2xl tabular-nums">{value}</div>
    </div>
  );
}
