# Hotel Cafe Ordering — Full Stack (v2)

QR-based ordering system for cafes & restaurants with three roles (customer, staff, admin), live kitchen updates, and a warm-artisan design.

- **Backend:** Python 3.11+, FastAPI, SQLite, JWT, bcrypt, WebSockets
- **Frontend:** Next.js 14, React 18, Tailwind CSS, Fraunces + Inter Tight, TypeScript

## Quick start

Open two terminals.

### 1) Backend (terminal 1)

```powershell
pip install -r requirements.txt
python seed_demo.py
python -m uvicorn app.main:app --reload
```

`seed_demo.py` prints a license key, admin/staff demo logins, and a sample QR URL.

### 2) Frontend (terminal 2)

```powershell
cd frontend
npm install
npm run dev
```

Then open:
- **Customer flow (QR target)** — http://localhost:3000/c/1/1
- **Staff & admin login** — http://localhost:3000/login

Demo accounts seeded by `seed_demo.py`:
- Admin: `admin@democafe.com` / `admin1234`
- Staff: `staff@democafe.com` / `staff1234`

## Demo storyline

1. Open `/c/1/1` as the customer — fill in your name + phone, browse the menu (with photos), add items, place the order
2. In an incognito tab, log in at `/login` as **staff** → live order appears instantly on `/staff/orders`
3. Walk it through `placed → preparing → ready → served` — the customer's order page updates live
4. Log in as **admin** → use `/admin/menu` to add a category, add an item with an image URL
5. Use `/admin/staff` to add a new staff user
6. Try logging in as the staff user and visiting `/admin/menu` → redirected away (role guard)

## Three-role auth

| Role | How they sign in | What they can do |
|---|---|---|
| Customer | QR scan → name + phone → 4-hour session token | Browse menu, place order, watch live status |
| Staff | Email + password | View all orders, advance status (no menu/team editing) |
| Admin | Email + password | Everything staff can + manage menu, tables, team |

Multi-tenant: every staff/admin request derives `cafe_id` from the verified JWT — clients cannot pick which cafe to operate on. Cross-cafe attempts return 403.

## Tests

```powershell
pytest -q
```

16 tests cover: end-to-end ordering flow (incl. WebSocket), cross-cafe isolation, forward-only status transitions, login, role separation (staff cannot reach admin endpoints), admin user management.

## Architecture

```
app/                    FastAPI backend
  main.py               app + WebSocket endpoints (/ws/staff, /ws/customer)
  db.py                 SQLite schema + migrations
  models.py             Pydantic schemas
  auth.py               JWT, bcrypt, role-based dependencies
  realtime.py           per-cafe WebSocket fan-out
  routers/
    auth.py             /auth/activate, /auth/login
    customer.py         /customer/checkin, /menu, /orders
    staff.py            /staff/orders (list + PATCH state)
    admin.py            /admin/categories, /menu-items, /tables, /users
frontend/               Next.js 14 app router
  app/
    page.tsx            landing
    c/[cafeId]/[tableId]/page.tsx   customer check-in (QR target)
    customer/menu/page.tsx          menu + cart
    customer/orders/[id]/page.tsx   live status
    login/page.tsx
    staff/orders/page.tsx           kitchen board (live)
    admin/menu/page.tsx
    admin/staff/page.tsx
  middleware.ts                     role-based route guards
  lib/{api,auth,ws,types}.ts
  components/DashboardShell.tsx
seed_demo.py            one-shot bootstrap
tests/                  pytest
```

## Production checklist (before going live)

- Set `HOTEL_JWT_SECRET` to a strong 32+ byte random string
- Tighten CORS in [app/main.py](app/main.py) — replace `allow_origins=["*"]` with your real domain
- Terminate TLS at a reverse proxy (nginx/Caddy) — WebSocket needs `wss://`
- Consider Postgres instead of SQLite (the layer is thin enough to swap)
- For multi-worker WS broadcast, replace the in-memory `ConnectionManager` with Redis pub/sub

## Future ideas (documented in [plan file](C:/Users/SCP/.claude/plans/hello-how-are-you-lively-noodle.md))

Call-waiter button, wait-time estimates from kitchen queue, out-of-stock toggle with instant push, multi-language menu, customer ratings, daily analytics, thermal printer ticket, split bill, WhatsApp receipts, offline-first PWA, per-cafe branding.

## Project Status

Feature branch: Hotel task board UI is under development.
