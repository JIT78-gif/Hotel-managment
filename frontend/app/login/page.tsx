"use client";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { saveStaffSession } from "@/lib/auth";
import type { LoginResponse } from "@/lib/types";

function LoginInner() {
  const router = useRouter();
  const search = useSearchParams();
  const next = search.get("next");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null); setBusy(true);
    try {
      const r = await api<LoginResponse>("/auth/login", {
        method: "POST", json: { email, password },
      });
      saveStaffSession(r);
      const fallback = r.role === "admin" ? "/admin/menu" : "/staff/orders";
      router.push(next || fallback);
    } catch (e: any) {
      setErr(e.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-dvh grid md:grid-cols-2">
      <div className="hidden md:flex relative overflow-hidden">
        <img
          src="https://images.unsplash.com/photo-1521017432531-fbd92d768814?w=1100&q=70&auto=format&fit=crop"
          alt="Cafe interior"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-tr from-ink/80 via-ink/40 to-transparent" />
        <div className="relative z-10 p-12 text-cream flex flex-col justify-end h-full">
          <span className="eyebrow text-terracotta-light">Staff &amp; admin only</span>
          <h2 className="display-lg text-cream mt-3">
            The kitchen<br /><em className="italic text-terracotta-light">never misses</em> an order.
          </h2>
          <p className="mt-4 text-cream/70 text-sm max-w-sm">
            Live tickets, status flow, menu control. Everything you need behind the pass.
          </p>
        </div>
      </div>

      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm animate-fade-up">
          <Link href="/" className="text-xs text-muted">← Back to landing</Link>
          <h1 className="display-lg mt-4">Sign in.</h1>
          <p className="text-muted mt-2 text-sm">Use the credentials given to you by your admin.</p>

          <form onSubmit={submit} className="mt-8 space-y-4">
            <div>
              <label className="label">Email</label>
              <input className="input" type="email" required autoComplete="email"
                value={email} onChange={e => setEmail(e.target.value)} placeholder="you@cafe.com" />
            </div>
            <div>
              <label className="label">Password</label>
              <input className="input" type="password" required autoComplete="current-password"
                value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" />
            </div>
            {err && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{err}</div>}
            <button type="submit" className="btn-primary w-full" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
            <p className="text-[11px] text-muted mt-3">
              Demo accounts (after running <code>seed_demo.py</code>):<br />
              admin@democafe.com / admin1234<br />
              staff@democafe.com / staff1234
            </p>
          </form>
        </div>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="p-12 text-center">Loading…</div>}>
      <LoginInner />
    </Suspense>
  );
}
