import Link from "next/link";
import { QrCode, ChefHat, Smartphone, ChevronRight } from "lucide-react";

export default function Landing() {
  return (
    <main className="min-h-dvh flex flex-col">
      <header className="px-5 md:px-12 py-4 md:py-6 flex items-center justify-between safe-top">
        <div className="flex items-center gap-1.5">
          <span className="font-display text-xl md:text-2xl italic">demo</span>
          <span className="font-display text-xl md:text-2xl">cafe</span>
        </div>
        <Link href="/login" className="btn-ghost text-xs md:text-sm">
          Staff &amp; Admin
          <ChevronRight size={14} />
        </Link>
      </header>

      {/* Mobile: stacked. Desktop: 2-column. */}
      <section className="flex-1 flex flex-col-reverse md:grid md:grid-cols-2 gap-8 md:gap-12
                          items-stretch md:items-center px-5 md:px-16 pb-10">
        {/* Copy */}
        <div className="animate-fade-up text-center md:text-left">
          <span className="eyebrow inline-flex items-center gap-2 justify-center md:justify-start">
            <Smartphone size={12} /> Hotel cafe · table-side ordering
          </span>
          <h1 className="display-xl mt-4">
            Scan, order,<br /><em className="text-terracotta italic font-display">enjoy.</em>
          </h1>
          <p className="mt-5 text-base md:text-lg text-muted max-w-md mx-auto md:mx-0 leading-relaxed">
            A quiet QR on every table. Guests browse the menu on their phone, the kitchen sees the order the moment it&apos;s placed — and you keep the hospitality where it belongs: at the table.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center md:justify-start">
            <Link href="/c/1/1" className="btn-primary justify-center">
              <QrCode size={18} /> Try the customer flow
            </Link>
            <Link href="/login" className="btn-secondary justify-center">
              <ChefHat size={18} /> Staff &amp; admin login
            </Link>
          </div>
        </div>

        {/* Hero image — smaller on mobile, anchored top */}
        <div className="relative h-[280px] sm:h-[360px] md:h-[560px] mt-2 md:mt-0">
          <div className="absolute inset-0 rounded-3xl overflow-hidden shadow-warm md:rotate-2">
            <img
              src="https://images.unsplash.com/photo-1559925393-8be0ec4767c8?w=1100&q=70&auto=format&fit=crop"
              alt="A warm cafe table with food laid out"
              className="w-full h-full object-cover"
            />
          </div>
          <div className="absolute -bottom-4 -left-2 md:-bottom-6 md:-left-6
                          card p-4 md:p-5 max-w-[230px] md:max-w-[260px] shadow-warm md:-rotate-2">
            <div className="flex items-center gap-2 text-[10px] md:text-xs text-muted uppercase tracking-[0.18em]">
              <span className="live-dot" /> Live to kitchen
            </div>
            <div className="mt-1.5 font-display text-base md:text-xl leading-snug">
              Table 4 just ordered<br /> <em className="text-terracotta italic">tomato soup</em>.
            </div>
          </div>
        </div>
      </section>

      <footer className="px-5 md:px-12 py-4 md:py-6 text-[11px] md:text-xs text-muted border-t border-parchment text-center md:text-left safe-bottom">
        Built for cafes, beach restaurants, and hotel dining rooms.
      </footer>
    </main>
  );
}
