# Deploying to EasyPanel

This stack is two Docker services (FastAPI backend + Next.js frontend) wired
together by `docker-compose.yml`. EasyPanel imports the compose file directly.

Estimated time: **15–20 minutes** end to end.

---

## 0. Before you start

You need:

- A VPS running EasyPanel (Hetzner / DigitalOcean / Contabo / etc.). Anything with **1 vCPU + 2 GB RAM** is plenty for the demo.
- A domain pointed at the VPS (e.g. `botifys.com`). DNS A record → VPS IP.
- The contents of this repository pushed to a Git host (GitHub / GitLab / Gitea).

---

## 1. Generate a JWT secret

On your laptop:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the output — you'll paste it as `HOTEL_JWT_SECRET` in step 4.

---

## 2. In EasyPanel — create a Project

EasyPanel UI → **Projects** → **Create Project** → name it `hotel-cafe`.

---

## 3. Create a Compose service from this repo

Inside the project: **Create Service** → **Compose**.

- **Source**: Git repository
- **Repository URL**: your fork's URL
- **Branch**: `main`
- **Compose file**: `docker-compose.yml` (default)

Click **Deploy**. EasyPanel pulls the repo and runs `docker compose build`.
First build takes 2–4 minutes (Python deps + Next.js build).

---

## 4. Set environment variables

In the same service → **Environment** tab, paste:

| Key | Value |
|---|---|
| `HOTEL_JWT_SECRET` | the long random string from step 1 |
| `HOTEL_CORS_ORIGINS` | `https://botifys.com` (your real domain) |
| `DEMO_ADMIN_EMAIL` | `admin@botifys.com` |
| `DEMO_ADMIN_PASSWORD` | a strong password you'll remember |
| `DEMO_STAFF_EMAIL` | `staff@botifys.com` |
| `DEMO_STAFF_PASSWORD` | a strong password |

**Redeploy** the service so the new env vars apply.

---

## 5. Configure the public domain

In the project → **Domains**:

- Domain: `botifys.com` (and optionally `www.botifys.com` as an alias)
- Service: **frontend**
- Port: **3000**

EasyPanel auto-provisions a free Let's Encrypt SSL certificate.

That single domain serves everything:
- `/` → Next.js frontend
- `/api/*` → proxied to backend by Next.js (server-side rewrite)
- `/ws/*` → **needs an extra route — see step 6**

---

## 6. Route WebSocket traffic to the backend

Next.js cannot proxy WebSocket upgrades through its `rewrites`. So you must add a second route in EasyPanel that sends `/ws/*` directly to the backend service.

Project → **Domains** → **Add Route**:

- Domain: `botifys.com`
- **Path**: `/ws`
- Service: **backend**
- Port: **8000**

This single rule covers both `/ws/staff` and `/ws/customer`. EasyPanel's Traefik proxy automatically handles the `Upgrade: websocket` header.

> **Verification**: open `https://botifys.com/ws/staff?token=junk` in the browser. You should get a `403 Forbidden` (the backend rejecting a bad token), **not** a 404 (frontend has no such route).

---

## 7. Seed the cafe (one-time)

EasyPanel → service `backend` → **Console** (terminal icon) → paste:

```bash
python seed_demo.py
```

Output prints the **cafe id**, a **sample table id**, and your admin/staff logins.

If you also want the full 210-item demo menu:

```bash
python seed_full_menu.py
```

> The script defaults to `http://127.0.0.1:8000` and the demo admin credentials.
> If you changed them, set `HOTEL_API_BASE`, `HOTEL_ADMIN_EMAIL`, and `HOTEL_ADMIN_PASSWORD` in the same Console before running.

---

## 8. Smoke test

Open in your browser:

| URL | Expected |
|---|---|
| `https://botifys.com/` | Landing page renders |
| `https://botifys.com/c/1` | Customer check-in form |
| `https://botifys.com/login` | Login form |
| `https://botifys.com/api/health` | `{"status":"ok"}` |

Log in with your admin email/password → see Orders + History + Menu + Team in the sidebar.
Place an order from `/c/1` in another tab → it lands on the staff dashboard instantly (this confirms the WebSocket route in step 6 is working).

---

## 9. Print QR codes

The QR for each table should encode `https://botifys.com/c/{cafe_id}`. Customers type their table number themselves on the check-in screen.

You can use any free QR generator. Suggested table-card layout:

```
┌─────────────────────────┐
│        BOTIFYS          │
│                         │
│      ┌─────────┐        │
│      │ QR CODE │        │
│      │   ███   │        │
│      │   ███   │        │
│      └─────────┘        │
│                         │
│  Scan to order. Type    │
│  your table number      │
│  when prompted.         │
└─────────────────────────┘
```

---

## Updating

After pushing changes to Git:

EasyPanel → service → **Redeploy**. It pulls, rebuilds, and rolls over without downtime (frontend takes ~90s to build, backend ~30s).

SQLite data is preserved between deployments — it lives on the named volume `hotel-data`.

---

## Backups

The DB is a single file at `/data/app.db` inside the backend container. To back up:

```bash
# From the EasyPanel host shell:
docker cp hotel-cafe-backend:/data/app.db ./app.db.$(date +%F).bak
```

Schedule that with `cron` weekly and you're set.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Frontend loads but `/api/*` returns 502 | Backend hasn't passed healthcheck yet — wait 30s; check `backend` logs |
| WebSocket stays "Offline" forever | Step 6 route missing — verify `/ws` path routes to backend on port 8000 |
| Can't log in after redeploy | `HOTEL_JWT_SECRET` changed → old tokens invalid → log in again |
| `seed_demo.py` says "Demo Cafe already exists" | Already seeded; skip step 7 |
| 500 on order placement after a long pause | Customer session expired (4-hour TTL) — re-scan the QR |

---

## Optional: scale to Postgres

For >1 cafe / >100 concurrent users, swap SQLite → Postgres:

1. In EasyPanel, add a **Postgres** service from the template gallery
2. Add SQLAlchemy (or `psycopg`) to `requirements.txt`, rewrite `app/db.py` to use Postgres
3. Run migrations
4. Drop the `hotel-data` volume

For the current demo scale (1 cafe, <50 concurrent diners), SQLite handles it without breaking a sweat.
