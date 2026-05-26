"use client";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { saveCustomerSession } from "@/lib/auth";

interface CheckinResp {
  session_token: string;
  expires_at: string;
  table_id: number;
  table_number: string;
}

export default function CheckinPage() {
  const params = useParams<{ cafeId: string }>();
  const router = useRouter();
  const cafe_id = Number(params.cafeId);

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [tableNumber, setTableNumber] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    if (phone.length !== 10) {
      setErr("Phone number must be 10 digits.");
      return;
    }
    setBusy(true);
    try {
      const r = await api<CheckinResp>("/customer/checkin", {
        method: "POST",
        json: {
          cafe_id,
          table_number: tableNumber.trim(),
          name: name.trim(),
          phone: `+91${phone}`,
        },
      });
      saveCustomerSession({
        session_token: r.session_token,
        cafe_id,
        table_id: r.table_id,
        table_number: r.table_number,
        name: name.trim(),
        expires_at: r.expires_at,
      });
      router.push("/customer/menu");
    } catch (e: any) {
      if (e.status === 404) {
        setErr("Couldn't find that table. Double-check the table number on your QR card.");
      } else {
        setErr(e.message || "Could not check in");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-dvh flex flex-col">
      <div className="relative h-44 sm:h-56 overflow-hidden">
        <img
          src="https://images.unsplash.com/photo-1559925393-8be0ec4767c8?w=1100&q=70&auto=format&fit=crop"
          alt=""
          aria-hidden="true"
          className="absolute inset-0 w-full h-full object-cover scale-110"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-ink/40 via-ink/10 to-cream" />
        <div className="absolute bottom-0 left-0 right-0 px-5 pb-3 text-cream text-center">
          <div className="text-[11px] uppercase tracking-[0.22em] opacity-90">Welcome</div>
          <div className="font-display text-xl italic">to the table</div>
        </div>
      </div>

      <div className="flex-1 px-4 -mt-6 pb-8 flex justify-center">
        <div className="w-full max-w-md animate-fade-up">
          <div className="card p-5 sm:p-7 space-y-5 shadow-warm">
            <div className="text-center">
              <h1 className="font-display text-3xl sm:text-4xl leading-tight">
                A few <em className="text-terracotta italic">quick details</em>.
              </h1>
              <p className="text-muted text-sm mt-2">
                Look at your table — the number is on the QR card.
              </p>
            </div>

            <form onSubmit={submit} className="space-y-4">
              <div>
                <label className="label" htmlFor="tablenum">Your table number</label>
                <input
                  id="tablenum"
                  className="input text-center font-display text-2xl tracking-wider"
                  required
                  maxLength={20}
                  autoComplete="off"
                  inputMode="text"
                  value={tableNumber}
                  onChange={e => setTableNumber(e.target.value)}
                  placeholder="e.g. T3"
                />
              </div>
              <div>
                <label className="label" htmlFor="name">Your name</label>
                <input
                  id="name"
                  className="input text-base"
                  required
                  maxLength={80}
                  autoComplete="given-name"
                  inputMode="text"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g. Aarav"
                />
              </div>
              <div>
                <label className="label" htmlFor="phone">Phone</label>
                <div className="flex items-stretch rounded-xl border border-parchment focus-within:border-terracotta focus-within:ring-2 focus-within:ring-terracotta/20 overflow-hidden bg-white">
                  <span
                    className="px-3 flex items-center text-muted text-base font-medium bg-parchment/40 border-r border-parchment select-none"
                    aria-hidden="true"
                  >
                    +91
                  </span>
                  <input
                    id="phone"
                    className="flex-1 px-3 py-2 text-base bg-transparent outline-none tabular-nums tracking-wide"
                    required
                    type="tel"
                    inputMode="numeric"
                    autoComplete="tel-national"
                    pattern="[0-9]{10}"
                    minLength={10}
                    maxLength={10}
                    value={phone}
                    onChange={e => setPhone(e.target.value.replace(/\D/g, "").slice(0, 10))}
                    placeholder="10-digit mobile number"
                  />
                </div>
                <p className="text-[11px] text-muted mt-1">For the bill / WhatsApp receipt</p>
              </div>

              {err && (
                <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {err}
                </div>
              )}

              <button type="submit" className="btn-primary w-full text-base" disabled={busy}>
                {busy ? "Just a moment…" : "Open the menu →"}
              </button>
              <p className="text-[11px] text-muted text-center leading-relaxed">
                We use your name &amp; phone only for this visit. No account, no spam.
              </p>
            </form>
          </div>
        </div>
      </div>
    </main>
  );
}
