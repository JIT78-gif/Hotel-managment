"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Hand, X, IndianRupee, Receipt, CheckCircle2, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { getStaffSession } from "@/lib/auth";
import { useStaffWs } from "@/lib/ws";
import type { AdminTable } from "@/lib/types";

interface TableBill {
  table_id: number;
  table_number: string;
  session: { name: string; phone: string; bill_requested: boolean; started_at: string; party_size: number };
  subtotal: number;
  gst_amount: number;
  grand_total: number;
  orders: BillOrder[];
}

interface BillOrder {
  id: number;
  status: string;
  subtotal: number;
  gst_amount: number;
  grand_total: number;
  instructions: string;
  placed_by?: string;
  created_at: string;
  items: { name: string; price: number; quantity: number }[];
}

function fmtTime(iso: string): string {
  const d = new Date(iso.includes("T") ? iso : iso.replace(" ", "T") + "Z");
  return isNaN(d.getTime()) ? iso : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function AdminTablesPage() {
  const [token, setToken] = useState<string | null>(null);
  const [tables, setTables] = useState<AdminTable[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [openTableId, setOpenTableId] = useState<number | null>(null);
  const [bill, setBill] = useState<TableBill | null>(null);
  const [billLoading, setBillLoading] = useState(false);
  const [marking, setMarking] = useState(false);
  const [newTableNumber, setNewTableNumber] = useState("");
  const [adding, setAdding] = useState(false);

  const load = useCallback(async (t: string) => {
    const data = await api<AdminTable[]>("/admin/tables", { staffToken: t });
    setTables(data);
  }, []);

  useEffect(() => {
    const s = getStaffSession();
    if (!s) return;
    setToken(s.token);
    load(s.token).catch(e => setErr(e.message));
  }, [load]);

  // Refresh table list whenever a relevant event arrives
  useStaffWs(token, (m) => {
    if (!token) return;
    if (m.event === "table_paid") {
      // Table just closed — the bill is gone. Just reload the list; don't try
      // to refresh a now-non-existent bill (that would 404).
      load(token).catch(() => {});
      if (openTableId === m.table?.id) closeSheet();
      return;
    }
    if (m.event === "bill_requested" || m.event === "new_order" || m.event === "status_changed") {
      load(token).catch(() => {});
      if (openTableId) loadBill(openTableId, token);
    }
  });

  async function loadBill(tableId: number, t: string) {
    setBillLoading(true);
    try {
      const data = await api<TableBill>(`/admin/tables/${tableId}/bill`, { staffToken: t });
      setBill(data);
    } catch (e: any) {
      if (e.status === 404) {
        // Table was paid/cleared between when we opened the sheet and now —
        // silently close instead of showing a confusing error
        closeSheet();
      } else {
        setErr(e.message);
      }
    } finally {
      setBillLoading(false);
    }
  }

  function openTable(t: AdminTable) {
    if (!t.is_occupied || !token) return;
    setOpenTableId(t.id);
    loadBill(t.id, token);
  }

  function closeSheet() {
    setOpenTableId(null);
    setBill(null);
  }

  async function addTable(e: React.FormEvent) {
    e.preventDefault();
    const tn = newTableNumber.trim();
    if (!tn || !token) return;
    setAdding(true); setErr(null);
    try {
      await api("/admin/tables", {
        method: "POST", staffToken: token, json: { table_number: tn },
      });
      setNewTableNumber("");
      await load(token);
    } catch (e: any) {
      if (e.status === 409) setErr(`A table named "${tn}" already exists.`);
      else setErr(e.message);
    } finally {
      setAdding(false);
    }
  }

  async function deleteTable(table: AdminTable) {
    if (!token) return;
    if (table.is_occupied) {
      setErr("Cannot delete an occupied table. Mark its bill paid first.");
      return;
    }
    if (!confirm(`Delete table "${table.table_number}"? Historical orders are preserved.`)) return;
    try {
      await api(`/admin/tables/${table.id}`, { method: "DELETE", staffToken: token });
      await load(token);
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function markPaid() {
    if (!openTableId || !token) return;
    if (!confirm(`Mark table ${bill?.table_number || openTableId} as paid? This clears the table and ends the customer's session.`)) return;
    setMarking(true);
    try {
      await api(`/admin/tables/${openTableId}/mark_paid`, { method: "POST", staffToken: token });
      closeSheet();
      await load(token);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setMarking(false);
    }
  }

  const summary = useMemo(() => {
    const occupied = tables.filter(t => t.is_occupied).length;
    const billRequested = tables.filter(t => t.session?.bill_requested).length;
    const revenueLive = tables.reduce((s, t) => s + (t.bill?.grand_total ?? 0), 0);
    return { occupied, billRequested, revenueLive, total: tables.length };
  }, [tables]);

  return (
    <div className="px-3 sm:px-5 md:px-10 py-4 sm:py-6 md:py-8">
      <header className="mb-4 sm:mb-6 md:mb-8">
        <span className="eyebrow">Floor</span>
        <h1 className="font-display text-3xl sm:text-4xl md:text-5xl leading-[1.05] tracking-tight mt-2">Tables.</h1>
        <p className="text-muted mt-1 text-xs sm:text-sm">Live status of every table. Tap an occupied table to see its bill.</p>
      </header>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3 mb-4 sm:mb-6">
        <Stat label="Tables" value={summary.total.toString()} />
        <Stat label="Occupied" value={summary.occupied.toString()} accent={summary.occupied > 0 ? "occupied" : undefined} />
        <Stat label="Bill req." value={summary.billRequested.toString()} accent={summary.billRequested > 0 ? "requested" : undefined} />
        <Stat label="Live ₹" value={`₹${summary.revenueLive.toFixed(0)}`} />
      </div>

      {err && (
        <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {err}
          <button onClick={() => setErr(null)} className="ml-2 underline">dismiss</button>
        </div>
      )}

      {/* Add table — stacks on phone, single row on tablet+ */}
      <form onSubmit={addTable} className="card p-3 mb-4 grid grid-cols-1 sm:grid-cols-[auto_1fr_auto] gap-2 items-center">
        <div className="flex items-center gap-2 text-sm text-muted">
          <Plus size={14} /> <span className="sm:inline">Add table</span>
        </div>
        <input
          className="input py-2 text-sm sm:text-base min-h-[44px]"
          placeholder="e.g. T7 (or 7 — both find T7)"
          value={newTableNumber}
          onChange={e => setNewTableNumber(e.target.value)}
          maxLength={20}
          inputMode="text"
          autoCorrect="off"
          autoCapitalize="characters"
        />
        <button className="btn-primary py-2 px-5 text-sm min-h-[44px]" disabled={adding || !newTableNumber.trim()}>
          {adding ? "Adding…" : "Add"}
        </button>
      </form>

      {tables.length === 0 ? (
        <div className="card p-8 sm:p-10 text-center text-muted">
          <div className="font-display text-xl">No tables yet.</div>
          <p className="text-sm mt-1">Use the form above to add your first table.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2 sm:gap-3">
          {tables.map(t => (
            <TableCard
              key={t.id}
              table={t}
              onClick={() => openTable(t)}
              onDelete={() => deleteTable(t)}
            />
          ))}
        </div>
      )}

      {/* Bill side-sheet */}
      {openTableId !== null && (
        <div className="fixed inset-0 z-50 flex md:items-stretch md:justify-end" role="dialog" aria-modal>
          <div className="absolute inset-0 bg-ink/55" onClick={closeSheet} />
          <aside className="relative w-full md:max-w-xl bg-cream
                            rounded-t-3xl md:rounded-none
                            mt-auto md:mt-0 max-h-[95dvh] md:max-h-none md:h-full
                            shadow-2xl flex flex-col animate-sheet-up md:animate-fade-up">
            <div className="md:hidden flex justify-center pt-2 pb-1 shrink-0">
              <div className="w-12 h-1.5 rounded-full bg-parchment" />
            </div>
            <header className="flex items-center justify-between px-5 md:px-6 py-3 md:py-5 border-b border-parchment shrink-0">
              <div>
                <div className="font-display text-2xl flex items-baseline gap-2">
                  <span>Table {bill?.table_number ?? ""}</span>
                  {bill && bill.session.party_size > 1 && (
                    <span className="badge bg-terracotta/15 text-terracotta-dark text-[10px]">
                      Party of {bill.session.party_size}
                    </span>
                  )}
                </div>
                {bill && (
                  <div className="text-xs text-muted mt-0.5">
                    {bill.session.name} · since {fmtTime(bill.session.started_at)}
                  </div>
                )}
              </div>
              <button onClick={closeSheet} className="btn-ghost p-2 min-h-[40px]" aria-label="Close">
                <X size={20} />
              </button>
            </header>

            <div className="flex-1 overflow-y-auto px-4 sm:px-5 md:px-6 py-3 sm:py-4 space-y-3 sm:space-y-4">
              {billLoading && <div className="text-sm text-muted">Loading bill…</div>}
              {bill && !billLoading && (
                <>
                  {bill.session.bill_requested && (
                    <div className="card p-3 bg-amber-50 border-amber-200 text-amber-900 text-sm flex items-start gap-2">
                      <Hand size={16} className="shrink-0 mt-0.5" />
                      <div>
                        <strong>Bill requested</strong> — the customer is waiting to pay.
                      </div>
                    </div>
                  )}

                  {/* Per-order breakdown */}
                  {bill.orders.map((o, i) => (
                    <article key={o.id} className="card p-3">
                      <header className="flex items-center justify-between text-xs text-muted mb-2">
                        <span>
                          Order #{o.id} · {fmtTime(o.created_at)}
                          {o.placed_by && bill.session.party_size > 1 && (
                            <span className="ml-2 text-terracotta">· by {o.placed_by}</span>
                          )}
                        </span>
                        <span className="badge badge-served capitalize">{o.status}</span>
                      </header>
                      <ul className="text-sm divide-y divide-parchment">
                        {o.items.map(it => (
                          <li key={`${o.id}-${it.name}`} className="flex justify-between py-1.5 gap-3">
                            <span className="min-w-0">
                              <span className="tabular-nums text-muted mr-2">×{it.quantity}</span>{it.name}
                            </span>
                            <span className="tabular-nums shrink-0">₹{(it.price * it.quantity).toFixed(0)}</span>
                          </li>
                        ))}
                      </ul>
                      {o.instructions && (
                        <div className="mt-2 text-xs italic text-terracotta-dark bg-terracotta/5 border border-terracotta/15 rounded px-2 py-1.5">
                          “{o.instructions}”
                        </div>
                      )}
                    </article>
                  ))}

                  {/* Combined totals */}
                  <section className="card p-4 bg-parchment/40">
                    <h3 className="font-display text-lg flex items-center gap-2 mb-3">
                      <Receipt size={16} className="text-terracotta" /> Combined bill
                    </h3>
                    <dl className="space-y-1 text-sm">
                      <div className="flex justify-between text-muted">
                        <dt>Subtotal ({bill.orders.length} order{bill.orders.length === 1 ? "" : "s"})</dt>
                        <dd className="tabular-nums">₹{bill.subtotal.toFixed(0)}</dd>
                      </div>
                      <div className="flex justify-between text-muted">
                        <dt>GST</dt>
                        <dd className="tabular-nums">₹{bill.gst_amount.toFixed(0)}</dd>
                      </div>
                      <div className="flex justify-between items-baseline pt-2 border-t border-parchment">
                        <dt className="font-medium">Grand total</dt>
                        <dd className="font-display text-3xl tabular-nums">₹{bill.grand_total.toFixed(0)}</dd>
                      </div>
                    </dl>
                  </section>
                </>
              )}
            </div>

            <div className="border-t border-parchment p-3 sm:p-4 md:p-6 safe-bottom shrink-0">
              <button onClick={markPaid} disabled={marking || !bill} className="btn-primary w-full h-14 text-base">
                <CheckCircle2 size={18} /> {marking ? "Marking paid…" : `Mark paid · ₹${(bill?.grand_total ?? 0).toFixed(0)}`}
              </button>
              <p className="text-[11px] text-muted text-center mt-2">
                This clears the table and ends the customer&apos;s session.
              </p>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: "occupied" | "requested" }) {
  const accentCls =
    accent === "occupied" ? "border-terracotta/30" :
    accent === "requested" ? "border-amber-300 bg-amber-50" :
    "";
  return (
    <div className={`card p-3 sm:p-4 border ${accentCls}`}>
      <div className="text-[10px] sm:text-[11px] uppercase tracking-[0.12em] sm:tracking-[0.14em] text-muted mb-0.5 sm:mb-1 truncate">{label}</div>
      <div className="font-display text-xl sm:text-2xl tabular-nums">{value}</div>
    </div>
  );
}

function TableCard({ table, onClick, onDelete }: {
  table: AdminTable;
  onClick: () => void;
  onDelete: () => void;
}) {
  const billRequested = table.session?.bill_requested;
  const occupied = table.is_occupied;

  const stateClass = billRequested
    ? "border-amber-400 bg-amber-50 ring-4 ring-amber-200 animate-pulse-dot"
    : occupied
    ? "border-terracotta/40 bg-cream"
    : "border-parchment bg-parchment/30 opacity-70";

  return (
    <div className={`card p-3 sm:p-4 transition border relative min-h-[88px] sm:min-h-[110px] ${stateClass}`}>
      <button
        onClick={onClick}
        disabled={!occupied}
        className={`absolute inset-0 w-full h-full rounded-2xl
                    ${occupied ? "hover:shadow-warm active:scale-[0.99] cursor-pointer" : "cursor-default"}`}
        aria-label={occupied ? `Open ${table.table_number} bill` : `Table ${table.table_number} idle`}
      />
      <div className="relative pointer-events-none">
        <div className="flex items-baseline justify-between gap-2 mb-1 sm:mb-2">
          <div className="font-display text-xl sm:text-2xl leading-tight truncate">{table.table_number}</div>
          <StateBadge billRequested={!!billRequested} occupied={occupied} />
        </div>
        {table.session && (
          <div className="text-[11px] sm:text-xs text-muted truncate mb-0.5">
            {table.session.name}
            {table.session.party_size && table.session.party_size > 1 && (
              <span className="ml-1 text-[9px] sm:text-[10px] uppercase tracking-wide text-terracotta">
                ({table.session.party_size}p)
              </span>
            )}
          </div>
        )}
        {table.bill && (
          <div className="text-xs sm:text-sm font-medium tabular-nums flex items-center gap-1 text-ink">
            <IndianRupee size={11} className="text-muted" />
            {table.bill.grand_total.toFixed(0)}
            <span className="text-[9px] sm:text-[10px] text-muted ml-1">· {table.bill.order_count} ord</span>
          </div>
        )}
      </div>
      {!occupied && (
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          className="absolute top-1 right-1 w-8 h-8 sm:w-7 sm:h-7 rounded-full text-muted hover:bg-red-50 hover:text-red-700 grid place-items-center transition pointer-events-auto"
          aria-label={`Delete table ${table.table_number}`}
          title="Delete table"
        >
          <Trash2 size={13} />
        </button>
      )}
    </div>
  );
}

function StateBadge({ billRequested, occupied }: { billRequested: boolean; occupied: boolean }) {
  if (billRequested) return <span className="badge bg-amber-200 text-amber-900 text-[9px]">BILL</span>;
  if (occupied) return <span className="badge bg-terracotta/15 text-terracotta-dark text-[9px]">IN USE</span>;
  return <span className="badge bg-stone-200 text-stone-600 text-[9px]">IDLE</span>;
}
