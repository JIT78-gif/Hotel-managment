"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Minus, Plus, ShoppingBag, X, Search, Receipt } from "lucide-react";
import { api } from "@/lib/api";
import { getCustomerSession } from "@/lib/auth";
import type { Menu, MenuItem } from "@/lib/types";

interface CartLine { item: MenuItem; qty: number }

function gstNoticeText(rate: number): string {
  if (!rate || rate <= 0) return "";
  return `Prices exclude ${rate % 1 === 0 ? rate.toFixed(0) : rate.toFixed(1)}% GST. Tax added at checkout.`;
}

export default function MenuPage() {
  const router = useRouter();
  const [menu, setMenu] = useState<Menu | null>(null);
  const [cart, setCart] = useState<Record<number, CartLine>>({});
  const [open, setOpen] = useState(false);
  const [activeCat, setActiveCat] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [instructions, setInstructions] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [placing, setPlacing] = useState(false);
  const headerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const s = getCustomerSession();
    if (!s) { router.push("/"); return; }
    api<Menu>("/customer/menu", { sessionToken: s.session_token })
      .then((m) => { setMenu(m); setActiveCat(m.categories[0]?.id ?? null); })
      .catch((e) => setErr(e.message));
  }, [router]);

  // Scroll-spy: highlight the category whose section is currently nearest the top of the viewport
  useEffect(() => {
    if (!menu) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter(e => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (!visible.length) return;
        const id = Number(visible[0].target.id.replace("cat-", ""));
        setActiveCat(id);
        const chip = document.querySelector<HTMLElement>(`[data-chip="${id}"]`);
        chip?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
      },
      { rootMargin: "-180px 0px -60% 0px", threshold: 0 }
    );
    menu.categories.forEach(c => {
      const el = document.getElementById(`cat-${c.id}`);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [menu]);

  function add(item: MenuItem) {
    setCart((c) => ({ ...c, [item.id]: { item, qty: (c[item.id]?.qty ?? 0) + 1 } }));
  }
  function dec(item: MenuItem) {
    setCart((c) => {
      const cur = c[item.id]?.qty ?? 0;
      const next = cur - 1;
      const copy = { ...c };
      if (next <= 0) delete copy[item.id];
      else copy[item.id] = { item, qty: next };
      return copy;
    });
  }

  const lines = Object.values(cart);
  const total = useMemo(() => lines.reduce((s, l) => s + l.item.price * l.qty, 0), [lines]);
  const itemCount = lines.reduce((s, l) => s + l.qty, 0);

  async function placeOrder() {
    const s = getCustomerSession();
    if (!s) { router.push("/"); return; }
    setPlacing(true); setErr(null);
    try {
      await api<{ order_id: number }>("/customer/orders", {
        method: "POST", sessionToken: s.session_token,
        json: {
          items: lines.map(l => ({ menu_item_id: l.item.id, quantity: l.qty })),
          instructions: instructions.trim(),
        },
      });
      setInstructions("");
      router.push("/customer/orders");
    } catch (e: any) { setErr(e.message); }
    finally { setPlacing(false); }
  }

  // GST calculations derived from menu.gst_rate
  const gstRate = menu?.gst_rate ?? 0;
  const gstAmount = total * gstRate / 100;
  const grandTotal = total + gstAmount;

  function jumpTo(catId: number) {
    setActiveCat(catId);
    const el = document.getElementById(`cat-${catId}`);
    if (!el) return;
    const h = headerRef.current?.getBoundingClientRect().height ?? 0;
    const y = el.getBoundingClientRect().top + window.scrollY - h - 8;
    window.scrollTo({ top: y, behavior: "smooth" });
  }

  if (err && !menu) return <ErrorScreen message={err} />;
  if (!menu) return <LoadingScreen />;
  const session = getCustomerSession();

  // Filter menu by search query
  const visible = query.trim()
    ? menu.categories
        .map(c => ({ ...c, items: c.items.filter(i =>
          i.name.toLowerCase().includes(query.toLowerCase()) ||
          i.description.toLowerCase().includes(query.toLowerCase())
        )}))
        .filter(c => c.items.length > 0)
    : menu.categories;

  return (
    <main className="min-h-dvh pb-32">
      {/* Sticky header */}
      <div ref={headerRef} className="sticky top-0 z-30 bg-cream/95 backdrop-blur-md border-b border-parchment">
        <div className="px-4 md:px-10 pt-4 pb-3 max-w-4xl mx-auto">
          <div className="flex items-baseline justify-between gap-3 mb-3">
            <div className="min-w-0">
              <div className="text-[11px] uppercase tracking-[0.18em] text-terracotta font-medium">
                Table {session?.table_number ?? `#${session?.table_id}`}
              </div>
              <h1 className="font-display text-2xl md:text-3xl leading-tight truncate">
                Hi {session?.name}<span className="text-muted">,</span> <em className="text-terracotta italic">order in</em>.
              </h1>
            </div>
            <Link
              href="/customer/orders"
              className="shrink-0 inline-flex items-center gap-1.5 rounded-full bg-parchment hover:bg-terracotta hover:text-cream text-ink px-3 py-1.5 text-xs font-medium transition active:scale-95"
              aria-label="Back to your orders"
            >
              <Receipt size={14} />
              <span className="hidden sm:inline">Your orders</span>
            </Link>
          </div>

          {/* Search */}
          <div className="relative">
            <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted/60 pointer-events-none" />
            <input
              type="search" value={query} onChange={e => setQuery(e.target.value)}
              placeholder="Search the menu…"
              className="input pl-10 py-2.5 text-sm bg-parchment/60 border-transparent focus:bg-cream"
            />
          </div>

          {/* GST notice */}
          {gstRate > 0 && (
            <div className="mt-2 text-[11px] text-muted text-center">
              * {gstNoticeText(gstRate)}
            </div>
          )}

          {/* Category chips */}
          <nav className="mt-3 flex gap-2 overflow-x-auto no-scrollbar snap-strip -mx-4 px-4 md:mx-0 md:px-0">
            {visible.map(c => (
              <button
                key={c.id}
                data-chip={c.id}
                onClick={() => jumpTo(c.id)}
                className={`shrink-0 rounded-full px-4 py-2 text-sm font-medium transition border whitespace-nowrap ${
                  activeCat === c.id
                    ? "bg-ink text-cream border-ink"
                    : "bg-cream text-ink border-parchment active:scale-95"
                }`}
              >
                {c.name}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Items */}
      <div className="px-4 md:px-10 py-6 space-y-10 max-w-4xl mx-auto">
        {visible.length === 0 && (
          <div className="text-center text-muted py-20">
            <div className="font-display text-2xl mb-2">Nothing matches</div>
            <div className="text-sm">Try a different search.</div>
          </div>
        )}
        {visible.map(c => (
          <section key={c.id} id={`cat-${c.id}`} className="scroll-mt-44">
            <h2 className="font-display text-2xl md:text-3xl mb-4 flex items-baseline justify-center gap-3 text-center">
              <span>{c.name}</span>
              <span className="text-[11px] uppercase tracking-widest text-muted font-sans">{c.items.length}</span>
            </h2>
            <ul className="space-y-3">
              {c.items.map(item => {
                const qty = cart[item.id]?.qty ?? 0;
                return (
                  <li key={item.id} className="card overflow-hidden">
                    <div className="flex gap-3 p-3">
                      <div className="flex-1 min-w-0 flex flex-col">
                        <h3 className="font-display text-lg leading-snug">{item.name}</h3>
                        {item.description && (
                          <p className="text-sm text-muted mt-1 leading-snug line-clamp-2">{item.description}</p>
                        )}
                        <div className="mt-auto pt-2 flex items-center gap-3">
                          <span className="font-medium tabular-nums">₹{item.price.toFixed(0)}</span>
                          {qty > 0 && (
                            <span className="text-[11px] text-terracotta font-medium">
                              ₹{(item.price * qty).toFixed(0)} subtotal
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="shrink-0 relative">
                        {item.image_url ? (
                          <img
                            src={item.image_url}
                            alt={item.name}
                            loading="lazy"
                            className="w-28 h-28 md:w-32 md:h-32 object-cover rounded-xl"
                          />
                        ) : (
                          <div className="w-28 h-28 md:w-32 md:h-32 bg-parchment rounded-xl grid place-items-center text-muted text-xs">
                            no image
                          </div>
                        )}
                        {/* Add / qty control overlays image bottom for that food-app feel */}
                        <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 w-[88%]">
                          {qty === 0 ? (
                            <button
                              onClick={() => add(item)}
                              className="w-full bg-cream text-ink border border-parchment shadow-soft rounded-full
                                         py-1.5 text-sm font-medium hover:bg-terracotta hover:text-cream
                                         active:scale-95 transition min-h-[36px]"
                            >
                              + Add
                            </button>
                          ) : (
                            <div className="bg-ink text-cream rounded-full shadow-warm flex items-center justify-between px-1 py-1 min-h-[36px]">
                              <button
                                onClick={() => dec(item)}
                                className="w-8 h-8 rounded-full hover:bg-terracotta flex items-center justify-center active:scale-90 transition"
                                aria-label={`Decrease ${item.name}`}
                              ><Minus size={14} /></button>
                              <span className="tabular-nums text-sm font-medium">{qty}</span>
                              <button
                                onClick={() => add(item)}
                                className="w-8 h-8 rounded-full hover:bg-terracotta flex items-center justify-center active:scale-90 transition"
                                aria-label={`Increase ${item.name}`}
                              ><Plus size={14} /></button>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>

      {/* Floating "View cart" pill — the food-app pattern */}
      {itemCount > 0 && !open && (
        <div className="fixed bottom-0 inset-x-0 z-40 safe-bottom px-4 pointer-events-none">
          <button
            onClick={() => setOpen(true)}
            className="pointer-events-auto mx-auto max-w-md w-full bg-ink text-cream rounded-full shadow-warm
                       flex items-center justify-between gap-4 px-5 py-3.5 active:scale-[0.98] transition animate-fade-up"
          >
            <span className="flex items-center gap-2">
              <span className="bg-terracotta text-cream w-7 h-7 rounded-full grid place-items-center text-xs font-medium tabular-nums">
                {itemCount}
              </span>
              <span className="font-medium">View cart</span>
            </span>
            <span className="flex items-center gap-2">
              <span className="tabular-nums">
                ₹{total.toFixed(0)}
                {gstRate > 0 && <span className="text-cream/60 text-xs ml-1">+GST</span>}
              </span>
              <ShoppingBag size={16} />
            </span>
          </button>
        </div>
      )}

      {/* Cart — full bottom sheet on mobile, right drawer on desktop */}
      {open && (
        <div className="fixed inset-0 z-50 flex md:justify-end" role="dialog" aria-modal>
          <div className="absolute inset-0 bg-ink/55" onClick={() => setOpen(false)} />
          <aside className="relative w-full md:max-w-md bg-cream md:h-full
                            rounded-t-3xl md:rounded-none
                            mt-auto md:mt-0 max-h-[92dvh] md:max-h-none
                            shadow-2xl flex flex-col animate-sheet-up md:animate-fade-up">
            {/* Drag handle on mobile */}
            <div className="md:hidden flex justify-center pt-2 pb-1">
              <div className="w-12 h-1.5 rounded-full bg-parchment" />
            </div>
            <div className="flex items-center justify-between px-5 md:px-6 py-3 md:py-5 border-b border-parchment">
              <h2 className="font-display text-2xl">Your order</h2>
              <button onClick={() => setOpen(false)} className="btn-ghost p-2 min-h-[40px]" aria-label="Close cart">
                <X size={20} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-5 md:px-6 py-4">
              {lines.length === 0 ? (
                <p className="text-muted text-sm py-16 text-center">Nothing in the cart yet.</p>
              ) : (
                <ul className="space-y-4">
                  {lines.map(l => (
                    <li key={l.item.id} className="flex justify-between items-center gap-3">
                      <div className="min-w-0">
                        <div className="font-medium truncate">{l.item.name}</div>
                        <div className="text-xs text-muted tabular-nums">₹{l.item.price.toFixed(0)} each</div>
                      </div>
                      <div className="inline-flex items-center gap-1 rounded-full bg-parchment pl-1 pr-1 py-1">
                        <button onClick={() => dec(l.item)} className="w-8 h-8 rounded-full hover:bg-terracotta hover:text-cream flex items-center justify-center active:scale-90 transition" aria-label="Remove one">
                          <Minus size={14} />
                        </button>
                        <span className="min-w-[28px] text-center tabular-nums text-sm">{l.qty}</span>
                        <button onClick={() => add(l.item)} className="w-8 h-8 rounded-full hover:bg-terracotta hover:text-cream flex items-center justify-center active:scale-90 transition" aria-label="Add one">
                          <Plus size={14} />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="border-t border-parchment p-5 md:p-6 space-y-3 safe-bottom">
              {/* Special instructions for the kitchen */}
              {lines.length > 0 && (
                <div>
                  <label className="text-[11px] uppercase tracking-[0.14em] text-muted block mb-1.5 font-medium">
                    Special requests <span className="lowercase opacity-60">(optional)</span>
                  </label>
                  <textarea
                    className="input min-h-[60px] resize-none text-sm"
                    maxLength={300}
                    placeholder="e.g. extra cheese, less spice, no onion"
                    value={instructions}
                    onChange={e => setInstructions(e.target.value)}
                  />
                </div>
              )}

              {/* Subtotal + GST + grand total breakdown */}
              {lines.length > 0 && (
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between text-muted">
                    <span>Subtotal</span>
                    <span className="tabular-nums">₹{total.toFixed(0)}</span>
                  </div>
                  {gstRate > 0 && (
                    <div className="flex justify-between text-muted">
                      <span>GST ({gstRate % 1 === 0 ? gstRate.toFixed(0) : gstRate.toFixed(1)}%)</span>
                      <span className="tabular-nums">₹{gstAmount.toFixed(0)}</span>
                    </div>
                  )}
                  <div className="flex justify-between items-baseline pt-2 border-t border-parchment">
                    <span className="font-medium">Grand total</span>
                    <span className="font-display text-3xl tabular-nums">₹{grandTotal.toFixed(0)}</span>
                  </div>
                </div>
              )}
              {err && <div className="text-sm text-red-700">{err}</div>}
              <button onClick={placeOrder} disabled={lines.length === 0 || placing} className="btn-primary w-full">
                {placing ? "Sending to kitchen…" : "Place order"}
              </button>
              <p className="text-[11px] text-muted text-center">You&apos;ll pay at the table.</p>
            </div>
          </aside>
        </div>
      )}
    </main>
  );
}

function LoadingScreen() {
  return (
    <div className="min-h-dvh grid place-items-center px-6">
      <div className="text-center animate-fade-up">
        <div className="w-12 h-12 rounded-full border-4 border-parchment border-t-terracotta animate-spin mx-auto mb-4" />
        <div className="text-muted text-sm">Loading the menu…</div>
      </div>
    </div>
  );
}

function ErrorScreen({ message }: { message: string }) {
  return (
    <div className="min-h-dvh grid place-items-center px-6">
      <div className="text-center max-w-sm">
        <h1 className="display-md mb-3">Couldn&apos;t load the menu.</h1>
        <p className="text-muted text-sm">{message}</p>
      </div>
    </div>
  );
}
