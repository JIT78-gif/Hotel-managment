"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ChefHat, ClipboardList, History, MessageSquare, Settings, Users, Utensils, UtensilsCrossed, LogOut } from "lucide-react";
import { getStaffSession, logoutStaff } from "@/lib/auth";
import type { LoginResponse } from "@/lib/types";

const navItems = [
  { href: "/staff/orders",   label: "Orders",   icon: ClipboardList,   roles: ["admin", "staff"] },
  { href: "/admin/tables",   label: "Tables",   icon: Utensils,        roles: ["admin"] },
  { href: "/staff/history",  label: "History",  icon: History,         roles: ["admin", "staff"] },
  { href: "/staff/feedback", label: "Feedback", icon: MessageSquare,   roles: ["admin", "staff"] },
  { href: "/admin/menu",     label: "Menu",     icon: UtensilsCrossed, roles: ["admin"] },
  { href: "/admin/staff",    label: "Team",     icon: Users,           roles: ["admin"] },
  { href: "/admin/settings", label: "Settings", icon: Settings,        roles: ["admin"] },
];

export default function DashboardShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [session, setSession] = useState<LoginResponse | null>(null);

  useEffect(() => {
    const s = getStaffSession();
    if (!s) { router.push(`/login?next=${encodeURIComponent(pathname)}`); return; }
    setSession(s);
  }, [router, pathname]);

  if (!session) return null;
  const visible = navItems.filter(n => n.roles.includes(session.role));

  function onLogout() {
    logoutStaff();
    router.push("/login");
  }

  return (
    <div className="min-h-dvh md:grid md:grid-cols-[260px_1fr]">
      <aside className="hidden md:flex flex-col bg-ink text-cream p-6 sticky top-0 h-dvh">
        <div className="flex items-center gap-2 mb-10">
          <ChefHat size={20} className="text-terracotta-light" />
          <span className="font-display text-xl">{session.cafe_name}</span>
        </div>
        <nav className="space-y-1 flex-1">
          {visible.map(n => {
            const active = pathname.startsWith(n.href);
            const I = n.icon;
            return (
              <Link key={n.href} href={n.href}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                  active ? "bg-cream text-ink" : "text-cream/70 hover:bg-white/5 hover:text-cream"
                }`}>
                <I size={16} />{n.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-white/10 pt-4 mt-4 text-xs">
          <div className="text-cream/60">Signed in as</div>
          <div className="font-medium truncate mt-0.5">{session.email}</div>
          <div className="mt-1"><span className="badge bg-white/10 text-cream/90">{session.role}</span></div>
          <button onClick={onLogout} className="mt-3 flex items-center gap-2 text-cream/70 hover:text-terracotta-light transition">
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <div className="md:hidden bg-ink text-cream px-4 py-3 flex items-center justify-between sticky top-0 z-30">
        <div className="font-display text-lg">{session.cafe_name}</div>
        <div className="flex items-center gap-2">
          {visible.map(n => {
            const active = pathname.startsWith(n.href);
            const I = n.icon;
            return (
              <Link key={n.href} href={n.href}
                className={`p-2 rounded-lg ${active ? "bg-cream text-ink" : "text-cream/80"}`}>
                <I size={16} />
              </Link>
            );
          })}
          <button onClick={onLogout} className="p-2 text-cream/80"><LogOut size={16} /></button>
        </div>
      </div>

      <main className="min-w-0">{children}</main>
    </div>
  );
}
