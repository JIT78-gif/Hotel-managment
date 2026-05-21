"use client";
import { useEffect, useMemo, useState } from "react";
import { Plus, Trash2, Image as ImageIcon, Pencil, X, Save } from "lucide-react";
import { api } from "@/lib/api";
import { getStaffSession } from "@/lib/auth";
import type { MenuItem } from "@/lib/types";

interface Category { id: number; name: string; sort_order: number }

export default function AdminMenuPage() {
  const [token, setToken] = useState<string | null>(null);
  const [cats, setCats] = useState<Category[]>([]);
  const [items, setItems] = useState<MenuItem[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState<number | "all">("all");
  const [editing, setEditing] = useState<MenuItem | null>(null);

  const [newCatName, setNewCatName] = useState("");
  const [newItem, setNewItem] = useState({
    category_id: "" as string, name: "", description: "", price: "", image_url: "",
  });

  async function refresh(t: string) {
    const [c, i] = await Promise.all([
      api<Category[]>("/admin/categories", { staffToken: t }),
      api<MenuItem[]>("/admin/menu-items", { staffToken: t }),
    ]);
    setCats(c); setItems(i);
  }

  useEffect(() => {
    const s = getStaffSession();
    if (!s) return;
    setToken(s.token);
    refresh(s.token).catch(e => setErr(e.message));
  }, []);

  const filteredItems = useMemo(() => {
    if (filter === "all") return items;
    return items.filter(i => i.category_id === filter);
  }, [items, filter]);

  async function addCategory(e: React.FormEvent) {
    e.preventDefault();
    if (!newCatName.trim() || !token) return;
    try {
      await api("/admin/categories", {
        method: "POST", staffToken: token,
        json: { name: newCatName.trim(), sort_order: cats.length },
      });
      setNewCatName("");
      await refresh(token);
    } catch (e: any) { setErr(e.message); }
  }

  async function deleteCategory(id: number) {
    if (!confirm("Delete this category AND all its items?")) return;
    try {
      await api(`/admin/categories/${id}`, { method: "DELETE", staffToken: token! });
      await refresh(token!);
    } catch (e: any) { setErr(e.message); }
  }

  async function addItem(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !newItem.category_id || !newItem.name) return;
    try {
      await api("/admin/menu-items", {
        method: "POST", staffToken: token,
        json: {
          category_id: Number(newItem.category_id),
          name: newItem.name,
          description: newItem.description,
          price: Number(newItem.price || 0),
          image_url: newItem.image_url,
        },
      });
      setNewItem({ category_id: newItem.category_id, name: "", description: "", price: "", image_url: "" });
      await refresh(token);
    } catch (e: any) { setErr(e.message); }
  }

  async function deleteItem(id: number) {
    if (!confirm("Delete this item?")) return;
    try {
      await api(`/admin/menu-items/${id}`, { method: "DELETE", staffToken: token! });
      await refresh(token!);
    } catch (e: any) { setErr(e.message); }
  }

  async function toggleAvail(it: MenuItem) {
    try {
      await api(`/admin/menu-items/${it.id}`, {
        method: "PATCH", staffToken: token!,
        json: { is_available: !it.is_available },
      });
      await refresh(token!);
    } catch (e: any) { setErr(e.message); }
  }

  async function saveEdit(updated: MenuItem) {
    try {
      await api(`/admin/menu-items/${updated.id}`, {
        method: "PATCH", staffToken: token!,
        json: {
          category_id: updated.category_id,
          name: updated.name,
          description: updated.description,
          price: updated.price,
          image_url: updated.image_url,
          is_available: updated.is_available,
        },
      });
      setEditing(null);
      await refresh(token!);
    } catch (e: any) { setErr(e.message); }
  }

  return (
    <div className="px-4 md:px-10 py-6 md:py-8 max-w-5xl">
      <header className="mb-6 md:mb-8">
        <span className="eyebrow">Admin</span>
        <h1 className="display-lg mt-2">The menu.</h1>
        <p className="text-muted mt-2 text-sm">
          Add categories first, then add items. Tap any item to edit name, description, price, image and availability.
        </p>
      </header>

      {err && (
        <div className="mb-6 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {err}
          <button onClick={() => setErr(null)} className="ml-2 underline">dismiss</button>
        </div>
      )}

      {/* Categories */}
      <section className="card p-4 md:p-6 mb-6">
        <h2 className="font-display text-xl mb-3">Categories <span className="text-sm text-muted">({cats.length})</span></h2>
        <form onSubmit={addCategory} className="flex gap-2 mb-4">
          <input className="input flex-1" placeholder="e.g. Desserts"
            value={newCatName} onChange={e => setNewCatName(e.target.value)} />
          <button className="btn-primary px-4 md:px-6"><Plus size={16} /><span className="hidden sm:inline">Add</span></button>
        </form>
        <ul className="flex flex-wrap gap-2">
          {cats.map(c => (
            <li key={c.id} className="inline-flex items-center gap-2 bg-parchment rounded-full pl-3 pr-1 py-1">
              <span className="text-sm">{c.name}</span>
              <button onClick={() => deleteCategory(c.id)}
                aria-label={`Delete ${c.name}`}
                className="text-muted hover:text-terracotta w-7 h-7 grid place-items-center rounded-full hover:bg-cream transition">
                <Trash2 size={13} />
              </button>
            </li>
          ))}
        </ul>
      </section>

      {/* Add item */}
      <section className="card p-4 md:p-6 mb-6">
        <h2 className="font-display text-xl mb-3">Add a menu item</h2>
        <form onSubmit={addItem} className="grid grid-cols-1 sm:grid-cols-6 gap-3">
          <select className="input sm:col-span-3" required
            value={newItem.category_id}
            onChange={e => setNewItem({ ...newItem, category_id: e.target.value })}>
            <option value="">Select category…</option>
            {cats.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <input className="input sm:col-span-3" placeholder="Name" required
            value={newItem.name}
            onChange={e => setNewItem({ ...newItem, name: e.target.value })} />
          <input className="input sm:col-span-2" placeholder="Price ₹" type="number" min={0} step="1" required
            value={newItem.price}
            onChange={e => setNewItem({ ...newItem, price: e.target.value })} />
          <input className="input sm:col-span-4" placeholder="Description"
            value={newItem.description}
            onChange={e => setNewItem({ ...newItem, description: e.target.value })} />
          <input className="input sm:col-span-5" placeholder="Image URL (https://images.unsplash.com/…)"
            value={newItem.image_url}
            onChange={e => setNewItem({ ...newItem, image_url: e.target.value })} />
          <button className="btn-primary sm:col-span-1"><Plus size={16} /></button>
        </form>
      </section>

      {/* Items list with filter */}
      <section>
        <div className="flex items-baseline justify-between mb-3 gap-3 flex-wrap">
          <h2 className="font-display text-xl">All items <span className="text-sm text-muted">({filteredItems.length}/{items.length})</span></h2>
          <select
            value={filter === "all" ? "all" : String(filter)}
            onChange={e => setFilter(e.target.value === "all" ? "all" : Number(e.target.value))}
            className="input py-1.5 text-sm max-w-[200px]"
          >
            <option value="all">All categories</option>
            {cats.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>

        <ul className="space-y-3">
          {filteredItems.map(it => {
            const cat = cats.find(c => c.id === it.category_id);
            return (
              <li key={it.id} className="card p-3 flex gap-3 items-center">
                {it.image_url ? (
                  <img src={it.image_url} alt={it.name}
                    className="w-16 h-16 sm:w-20 sm:h-20 object-cover rounded-xl shrink-0" />
                ) : (
                  <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-xl bg-parchment grid place-items-center text-muted shrink-0">
                    <ImageIcon size={18} />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="font-display text-base sm:text-lg leading-snug truncate">{it.name}</div>
                  <div className="text-[11px] text-muted truncate">{cat?.name ?? "—"}</div>
                  {it.description && (
                    <div className="text-xs text-muted mt-0.5 truncate hidden sm:block">{it.description}</div>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <div className="font-medium tabular-nums text-sm sm:text-base">₹{it.price.toFixed(0)}</div>
                  <button
                    onClick={() => toggleAvail(it)}
                    className={`badge mt-1 text-[10px] ${
                      it.is_available ? "bg-emerald-100 text-emerald-900" : "bg-stone-200 text-stone-700"
                    }`}
                  >
                    {it.is_available ? "On" : "Off"}
                  </button>
                </div>
                <div className="flex flex-col gap-1 shrink-0">
                  <button onClick={() => setEditing(it)}
                    aria-label={`Edit ${it.name}`}
                    className="w-9 h-9 rounded-full bg-parchment text-ink hover:bg-terracotta hover:text-cream grid place-items-center transition">
                    <Pencil size={14} />
                  </button>
                  <button onClick={() => deleteItem(it.id)}
                    aria-label={`Delete ${it.name}`}
                    className="w-9 h-9 rounded-full text-muted hover:bg-red-50 hover:text-red-700 grid place-items-center transition">
                    <Trash2 size={14} />
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      </section>

      {editing && (
        <EditItemSheet
          item={editing}
          categories={cats}
          onClose={() => setEditing(null)}
          onSave={saveEdit}
        />
      )}
    </div>
  );
}

function EditItemSheet({
  item, categories, onClose, onSave,
}: {
  item: MenuItem;
  categories: Category[];
  onClose: () => void;
  onSave: (updated: MenuItem) => Promise<void>;
}) {
  const [draft, setDraft] = useState<MenuItem>(item);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true); setErr(null);
    try {
      await onSave(draft);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex md:items-center md:justify-center" role="dialog" aria-modal>
      <div className="absolute inset-0 bg-ink/55" onClick={onClose} />
      <aside className="relative w-full md:max-w-xl bg-cream md:rounded-3xl
                        rounded-t-3xl mt-auto md:mt-0 max-h-[95dvh] md:max-h-[90dvh]
                        shadow-2xl flex flex-col animate-sheet-up md:animate-fade-up">
        <div className="md:hidden flex justify-center pt-2 pb-1 shrink-0">
          <div className="w-12 h-1.5 rounded-full bg-parchment" />
        </div>
        <div className="flex items-center justify-between px-5 md:px-6 py-3 md:py-5 border-b border-parchment shrink-0">
          <h2 className="font-display text-2xl">Edit item</h2>
          <button onClick={onClose} aria-label="Close" className="btn-ghost p-2 min-h-[40px]">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={submit} className="flex-1 overflow-y-auto px-5 md:px-6 py-4 space-y-4">
          {/* Image preview */}
          {draft.image_url && (
            <div className="rounded-2xl overflow-hidden bg-parchment">
              <img src={draft.image_url} alt={draft.name}
                className="w-full h-44 object-cover" />
            </div>
          )}

          <div>
            <label className="label">Category</label>
            <select className="input"
              value={String(draft.category_id ?? "")}
              onChange={e => setDraft({ ...draft, category_id: Number(e.target.value) })}>
              {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>

          <div>
            <label className="label">Name</label>
            <input className="input text-base" required maxLength={120}
              value={draft.name}
              onChange={e => setDraft({ ...draft, name: e.target.value })} />
          </div>

          <div>
            <label className="label">Description</label>
            <textarea className="input min-h-[80px] resize-none" maxLength={400}
              value={draft.description}
              onChange={e => setDraft({ ...draft, description: e.target.value })} />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Price (₹)</label>
              <input className="input text-base" type="number" min={0} step="1" required
                value={draft.price}
                onChange={e => setDraft({ ...draft, price: Number(e.target.value) })} />
            </div>
            <div>
              <label className="label">Available</label>
              <button type="button"
                onClick={() => setDraft({ ...draft, is_available: !draft.is_available })}
                className={`input w-full text-left flex items-center justify-between ${
                  draft.is_available ? "bg-emerald-50 border-emerald-200" : "bg-stone-100 border-stone-300"
                }`}>
                <span>{draft.is_available ? "Available" : "Off the menu"}</span>
                <span className={`w-10 h-5 rounded-full relative transition ${
                  draft.is_available ? "bg-emerald-500" : "bg-stone-400"
                }`}>
                  <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-cream transition ${
                    draft.is_available ? "left-5" : "left-0.5"
                  }`} />
                </span>
              </button>
            </div>
          </div>

          <div>
            <label className="label">Image URL</label>
            <input className="input text-sm"
              placeholder="https://images.unsplash.com/photo-…"
              value={draft.image_url}
              onChange={e => setDraft({ ...draft, image_url: e.target.value })} />
            <p className="text-[11px] text-muted mt-1">
              Tip: search <a href="https://unsplash.com" target="_blank" rel="noreferrer" className="underline">unsplash.com</a>,
              right-click any image → Copy image address.
            </p>
          </div>

          {err && (
            <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {err}
            </div>
          )}
        </form>

        <div className="border-t border-parchment p-4 md:p-6 flex gap-2 safe-bottom shrink-0">
          <button onClick={onClose} className="btn-secondary flex-1">Cancel</button>
          <button onClick={submit} disabled={saving} className="btn-primary flex-1">
            {saving ? "Saving…" : (<><Save size={16} /> Save</>)}
          </button>
        </div>
      </aside>
    </div>
  );
}
