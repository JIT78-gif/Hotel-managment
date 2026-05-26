"use client";
import { useEffect, useState } from "react";
import { Save, Percent, Building } from "lucide-react";
import { api } from "@/lib/api";
import { getStaffSession } from "@/lib/auth";
import type { CafeInfo } from "@/lib/types";

const PRESET_RATES = [0, 5, 12, 18];

export default function AdminSettingsPage() {
  const [token, setToken] = useState<string | null>(null);
  const [cafe, setCafe] = useState<CafeInfo | null>(null);
  const [gstRate, setGstRate] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const s = getStaffSession();
    if (!s) return;
    setToken(s.token);
    api<CafeInfo>("/admin/cafe", { staffToken: s.token })
      .then(c => { setCafe(c); setGstRate(String(c.gst_rate)); })
      .catch(e => setErr(e.message));
  }, []);

  async function save() {
    if (!token) return;
    const n = Number(gstRate);
    if (isNaN(n) || n < 0 || n > 28) {
      setErr("GST rate must be a number between 0 and 28.");
      return;
    }
    setSaving(true); setErr(null); setSaved(false);
    try {
      const c = await api<CafeInfo>("/admin/cafe", {
        method: "PATCH", staffToken: token, json: { gst_rate: n },
      });
      setCafe(c);
      setGstRate(String(c.gst_rate));
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  if (!cafe) return <div className="p-10 text-muted text-sm">Loading…</div>;

  return (
    <div className="px-4 md:px-10 py-6 md:py-8 max-w-2xl">
      <header className="mb-6 md:mb-8">
        <span className="eyebrow">Admin</span>
        <h1 className="display-lg mt-2">Settings.</h1>
        <p className="text-muted mt-1 text-sm">Cafe-wide configuration.</p>
      </header>

      <section className="card p-5 md:p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <Building size={16} className="text-terracotta" />
          <h2 className="font-display text-xl">{cafe.name}</h2>
        </div>

        <div className="space-y-2 text-sm">
          <div className="flex justify-between text-muted">
            <span>Cafe ID</span>
            <span className="tabular-nums">#{cafe.id}</span>
          </div>
          <div className="flex justify-between text-muted">
            <span>Current GST rate</span>
            <span className="tabular-nums">{cafe.gst_rate}%</span>
          </div>
        </div>
      </section>

      <section className="card p-5 md:p-6">
        <div className="flex items-center gap-3 mb-4">
          <Percent size={16} className="text-terracotta" />
          <h2 className="font-display text-xl">GST rate</h2>
        </div>
        <p className="text-sm text-muted mb-4">
          Tax added at checkout. Shown to customers as a separate line on their bill.
          Indian restaurants typically use 5% (regular) or 18% (with input tax credit).
        </p>

        <div className="flex flex-wrap gap-2 mb-3">
          {PRESET_RATES.map(r => (
            <button
              key={r}
              onClick={() => setGstRate(String(r))}
              className={`rounded-full px-4 py-2 text-sm font-medium border transition ${
                Number(gstRate) === r
                  ? "bg-ink text-cream border-ink"
                  : "bg-cream text-ink border-parchment hover:border-terracotta"
              }`}
            >
              {r}%
            </button>
          ))}
        </div>

        <label className="label" htmlFor="gst-input">Custom rate (0–28%)</label>
        <div className="flex gap-2">
          <input
            id="gst-input"
            type="number"
            step="0.5"
            min={0}
            max={28}
            value={gstRate}
            onChange={e => setGstRate(e.target.value)}
            className="input flex-1 text-base"
          />
          <button onClick={save} disabled={saving} className="btn-primary">
            <Save size={16} /> {saving ? "Saving…" : "Save"}
          </button>
        </div>

        {err && (
          <div className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {err}
          </div>
        )}
        {saved && (
          <div className="mt-3 text-sm text-forest bg-forest/10 border border-forest/20 rounded-lg px-3 py-2">
            Saved. Future orders will use {cafe.gst_rate}% GST. Existing orders keep the rate they were placed under.
          </div>
        )}
      </section>
    </div>
  );
}
