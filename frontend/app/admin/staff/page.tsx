"use client";
import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { getStaffSession } from "@/lib/auth";
import type { UserOut } from "@/lib/types";

export default function AdminStaffPage() {
  const [token, setToken] = useState<string | null>(null);
  const [users, setUsers] = useState<UserOut[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [form, setForm] = useState({ email: "", password: "", role: "staff" as "admin" | "staff" });

  async function refresh(t: string) {
    setUsers(await api<UserOut[]>("/admin/users", { staffToken: t }));
  }

  useEffect(() => {
    const s = getStaffSession();
    if (!s) return;
    setToken(s.token);
    refresh(s.token).catch(e => setErr(e.message));
  }, []);

  async function addUser(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setErr(null);
    try {
      await api("/admin/users", { method: "POST", staffToken: token, json: form });
      setForm({ email: "", password: "", role: "staff" });
      await refresh(token);
    } catch (e: any) { setErr(e.message); }
  }

  async function deleteUser(id: number) {
    if (!confirm("Delete this user?")) return;
    try {
      await api(`/admin/users/${id}`, { method: "DELETE", staffToken: token! });
      await refresh(token!);
    } catch (e: any) { setErr(e.message); }
  }

  return (
    <div className="px-4 md:px-10 py-6 md:py-8 max-w-3xl">
      <header className="mb-6 md:mb-8">
        <span className="eyebrow">Admin</span>
        <h1 className="display-lg mt-2">The team.</h1>
        <p className="text-muted mt-2 text-sm">Only admins can add staff. Staff can see and update orders. Admins can do everything.</p>
      </header>

      {err && <div className="mb-6 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{err}</div>}

      <section className="card p-4 md:p-6 mb-6">
        <h2 className="font-display text-xl mb-3">Add a teammate</h2>
        <form onSubmit={addUser} className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <input className="input sm:col-span-2 text-base" type="email" placeholder="email" required autoComplete="email"
            value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
          <input className="input text-base" type="password" placeholder="password (min 6)" required minLength={6} autoComplete="new-password"
            value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} />
          <div className="flex gap-2">
            <select className="input flex-1" value={form.role}
              onChange={e => setForm({ ...form, role: e.target.value as any })}>
              <option value="staff">Staff</option>
              <option value="admin">Admin</option>
            </select>
            <button className="btn-primary px-4" aria-label="Add teammate"><Plus size={16} /></button>
          </div>
        </form>
      </section>

      <section>
        <h2 className="font-display text-xl mb-4">Team <span className="text-sm text-muted">({users.length})</span></h2>
        <ul className="space-y-3">
          {users.map(u => (
            <li key={u.id} className="card p-4 flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-terracotta/15 text-terracotta grid place-items-center font-display text-lg">
                {u.email[0]?.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{u.email}</div>
                <div className="text-xs text-muted">since {u.created_at}</div>
              </div>
              <span className={`badge ${u.role === "admin" ? "bg-terracotta/15 text-terracotta-dark" : "bg-forest/10 text-forest"}`}>
                {u.role}
              </span>
              <button onClick={() => deleteUser(u.id)} className="text-muted hover:text-terracotta p-2"><Trash2 size={15} /></button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
