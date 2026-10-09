# Deploying VeriFi on Render

This guide deploys the code in this repository: a **FastAPI** backend
(`app/`), a **React 18 + Vite + TypeScript** frontend (`frontend/`),
**SQLAlchemy + Alembic** on **PostgreSQL**, and optional external providers
(Groq/OpenAI, SerpAPI/Tavily, Alpha Vantage, SEC EDGAR, Google OAuth,
Resend). There is no Express, Prisma, Hardhat, Solidity or wallet code in
this repository, so those topics don't apply (see section 16).

---

## 1. Architecture

```
                    Render (region: Singapore)
   ┌────────────────────────────────────────────────────────────┐
   │  Web Service "verifi"  (Docker, ./Dockerfile)              │
   │   stage 1: node:22   npm ci && npm run build  -> dist/     │
   │   stage 2: python:3.13  uvicorn app.main:app  :$PORT       │
   │     /api/*   FastAPI routes (research, industries, ipos,   │
   │              auth, health)                                  │
   │     /        built React app (same origin as /api)         │
   └──────────────────────────┬─────────────────────────────────┘
                              │ DATABASE_URL (internal)
   ┌──────────────────────────▼─────────────────────────────────┐
   │  PostgreSQL "verifi-db" (managed, persistent)              │
   └────────────────────────────────────────────────────────────┘
```

**Option A, the default (`render.yaml`), is one Web Service + one database.**
The Docker image builds the frontend and FastAPI serves it
(`app/main.py` mounts `frontend/dist`). The browser talks to a single
origin, so the HttpOnly session cookie, Google sign-in and magic links work
without CORS or third-party cookies. This is the existing architecture, and
it's the most reliable one.

**Option B** puts the frontend on a separate **Render Static Site**. The code
supports it (`VITE_API_BASE_URL`, `CORS_ORIGINS`, `SESSION_COOKIE_SAMESITE`),
but read section 10 before choosing it.

## 2. Prerequisites

- A GitHub repository containing this code (Render deploys from GitHub).
- A Render account. Everything below works on the free plans, with the
  limits in section 19.
- Optional credentials, depending on the features you want (section 6).

Nothing else needs to be installed on your machine to deploy.

## 3. Render Web Service settings (Option A)

Blueprint users get these from `render.yaml` automatically. For a manual
setup (**New → Web Service**):

| Setting | Value |
|---|---|
| Repository / branch | your repo, `main` |
| Language / runtime | **Docker** |
| Root directory | *(empty, repo root)* |
| Dockerfile path | `./Dockerfile` |
| Docker build context | `.` |
| Region | Singapore (closest to NSE and Indian users) |
| Instance type | Free to try. **Standard (2 GB)** if `RAG_ENABLED=true` |
| Health check path | `/api/health` |
| Auto-deploy | On commit |

There are no build or start commands to enter. The Dockerfile builds the
frontend (`npm ci && npm run build`), installs Python dependencies (CPU-only
torch first, then `requirements.txt`), and starts:

```
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'
```

`--proxy-headers` makes FastAPI see Render's HTTPS scheme, so redirects and
Secure cookies are correct.

## 4. Render Static Site settings (Option B only)

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Build command | `npm ci && npm run build` |
| Publish directory | `dist` (relative to `frontend`) |
| Environment variable | `VITE_API_BASE_URL=https://<your-web-service>.onrender.com` |
| Redirects/Rewrites | Rewrite `/*` → `/index.html` |

The app has no client-side router (views are switched in React state), so
every page lives at `/`. The rewrite only makes a refresh on any unexpected
path land back on the app.

## 5. Build and start commands at a glance

| Purpose | Command | Where |
|---|---|---|
| Frontend build | `npm ci && npm run build` | `frontend/` (inside the Dockerfile) |
| Frontend type check | `npm run check` | `frontend/` |
| Backend deps | `pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.0 && pip install -r requirements.txt` | Dockerfile |
| Start | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'` | Dockerfile `CMD` |
| Migrations | run automatically on startup (`app/storage/database.py: run_migrations`) | - |
| Tests | `python -m pytest` | repo root |

## 6. Environment variables

### Web service

| Variable | Required | Value / notes |
|---|---|---|
| `DATABASE_URL` | yes | From the Render database (`fromDatabase` in the Blueprint). `postgres://` and `postgresql://` URLs are normalised to the installed psycopg 3 driver automatically. |
| `DEMO_MODE` | yes | `false` for real data. `true` forces labelled sample providers. |
| `SESSION_COOKIE_SECURE` | yes | `true` (Render serves HTTPS). |
| `OAUTH_STATE_SECRET` | yes | Any long random string (`generateValue: true` in the Blueprint). Signs the short-lived Google OAuth state cookie. |
| `RAG_ENABLED` | yes | `false` on 512 MB plans. `true` only with 2 GB or more (section 19). |
| `LOG_LEVEL` | no | `INFO` |
| `LLM_PROVIDER` | no | `groq` (default) or `openai` |
| `GROQ_API_KEY` / `OPENAI_API_KEY` | for live research | Without an LLM key the research pipeline runs in labelled demo mode. Industry data and IPO pages still work. |
| `GROQ_MODEL`, `OPENAI_MODEL`, `LLM_TPM_LIMIT` | no | Model and tokens-per-minute pacing (`openai/gpt-oss-20b`, `7000`). |
| `SEARCH_PROVIDER` | no | `serpapi` or `tavily` |
| `SERPAPI_API_KEY` / `TAVILY_API_KEY` | for web sources | Without it, research uses filings and financial APIs only. |
| `ALPHAVANTAGE_API_KEY` | no | Falls back to yfinance when unset. |
| `SEC_EDGAR_USER_AGENT` | recommended | A descriptive UA with a contact email (SEC fair-access policy). |
| `MAX_FOLLOWUP_ITERATIONS`, `MAX_SUBQUERIES_PER_PLAN` | no | Research loop limits (`0`, `4`). |
| `APP_BASE_URL` | no | Defaults to Render's `RENDER_EXTERNAL_URL`. Set it only for a custom domain. It must match the Google OAuth redirect URI exactly. |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | no | Enables "Continue with Google". Hidden when unset. |
| `BREVO_API_KEY` / `BREVO_SENDER_EMAIL` | no | Magic-link sign-in to **any** inbox without owning a domain: verify one sender address in Brevo (Senders). Preferred over Resend when set. |
| `RESEND_API_KEY` / `RESEND_FROM_EMAIL` | no | Magic-link sign-in via Resend. Sends only to your own Resend account address until you verify a domain. Hidden when neither email provider is set. |
| `CORS_ORIGINS` | Option B only | Exact frontend origin(s), comma-separated, e.g. `https://verifi-web.onrender.com`. Leave empty for Option A. |
| `FRONTEND_URL` | Option B only | Where sign-in redirects back to. |
| `SESSION_COOKIE_SAMESITE` | Option B only | `none` (forces `Secure`). The default `lax` is right for Option A. |

### Static site (Option B only)

| Variable | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://<your-web-service>.onrender.com` (no trailing slash) |

Every `VITE_` variable is compiled into public JavaScript. **Never put a key
in one.** All provider keys above live only on the web service.

## 7. Database: migrations

- The schema is owned by Alembic (`migrations/versions/`).
  `init_db()` runs `alembic upgrade head` **on every startup**. Applying
  migrations is idempotent and non-destructive: it only adds what is
  missing.
- First deploy: the empty Render database is migrated to the latest
  revision (`c2f4a7e91b3d`) automatically. Verified locally against a fresh
  PostgreSQL 16 database: all 16 tables created.
- The `pgvector` extension is created only if the server offers it. No
  table uses a vector column yet, so a database without pgvector deploys
  fine.
- Changing the schema later: edit `app/storage/models.py`, then
  `alembic revision --autogenerate -m "..."` locally, review the file,
  commit. The next deploy applies it.
- **Never** run `alembic downgrade` against production without a backup.

## 8. Database: provisioning, seeding and persistence

- **Provision**: the Blueprint creates `verifi-db`. Manually: **New →
  PostgreSQL**, same region as the web service, then copy its **Internal
  Database URL** into the web service's `DATABASE_URL`.
- **Persistence**: data lives in the managed database, not in the
  container. The container filesystem is ephemeral, so the SQLite fallback
  is **not** suitable on Render, and `data/` is excluded from the image.
- **Industry data fills itself**: on startup the server syncs the ten
  NIFTY IT companies' filings from the exchange API in the background
  (`app/datastore/sync.py`). Against an empty database this took about 6 s
  locally. If the exchange API rejects requests from Render's network, the
  dashboard stays empty: check the logs (section 15) and use the
  copy-from-local route below.
- **IPO data must be seeded** once. From the service's **Shell** tab (paid
  plans):
  ```
  python -m scripts.seed_ipo
  ```
  Or, on any plan, from your machine with the database's **External**
  URL:
  ```
  DATABASE_URL="postgresql://...render.com/verifi" python -m scripts.seed_ipo
  ```
- **Copying your local database** (accounts, research runs, filings):
  ```
  docker exec verifi-db pg_dump -U verifi -Fc verifi > verifi.dump
  pg_restore --no-owner --no-acl -d "<Render external URL>" verifi.dump
  ```
  Do this before the first deploy, or onto an empty database. Restoring
  over existing data creates conflicts.

## 9. Local development vs production

| | Local | Render |
|---|---|---|
| Start | `.\scripts\dev.ps1` / `./scripts/dev.sh` (Postgres container + `uvicorn --reload`) | Dockerfile `CMD` |
| Frontend | `npm run dev` on :5173, Vite proxies `/api` → :8000 | built into the image, same origin |
| Database | `verifi-db` container on :5434 (`docker compose up -d db`) | Render PostgreSQL |
| Config | `.env` (git-ignored) | Render environment variables |
| Cookies | `SESSION_COOKIE_SECURE=false` | `true` |

`.env` is git-ignored and excluded from the Docker image (`.dockerignore`).
Use `.env.example` and `frontend/.env.example` as templates.

## 10. CORS and frontend-to-backend connection

**Option A** needs no CORS at all: the frontend calls relative `/api/...`
URLs (`frontend/src/services/api.ts`, `API_BASE` empty), and no CORS headers
are sent.

**Option B (separate Static Site)**:

1. Static site: `VITE_API_BASE_URL=https://verifi.onrender.com`. Requests
   then go to that origin with `credentials: "include"`.
2. Web service: `CORS_ORIGINS=https://verifi-web.onrender.com`,
   `FRONTEND_URL=https://verifi-web.onrender.com`,
   `SESSION_COOKIE_SAMESITE=none`.
3. Google OAuth redirect URI stays on the **API** host
   (`https://verifi.onrender.com/api/auth/google/callback`).

**Caveat:** `onrender.com` is on the Public Suffix List, so two
`*.onrender.com` services are *different sites*. The session cookie
then becomes a third-party cookie, which Safari blocks by default and other
browsers increasingly restrict, and users would appear logged out
immediately after signing in. Option B is only dependable when both
services share a custom parent domain (e.g. `app.example.com` +
`api.example.com`). Otherwise use Option A.

## 11. Deploying with the Blueprint

1. Push this repository (including `render.yaml`) to GitHub.
2. Render dashboard → **New → Blueprint** → choose the repository.
3. Render shows `verifi` (web) and `verifi-db` (PostgreSQL). Fill in
   the `sync: false` secrets you have (blanks are fine for optional ones).
4. **Apply**. The first build takes several minutes (Python ML
   dependencies).
5. When it's live, seed the IPO data (section 8) and check health
   (section 14).
6. Google sign-in: add
   `https://<service>.onrender.com/api/auth/google/callback` as an
   authorised redirect URI in Google Cloud Console, and add your Gmail to
   the OAuth app's test users while it is in Testing.

## 12. Deploying manually (no Blueprint)

1. **New → PostgreSQL**: name `verifi-db`, region Singapore, PostgreSQL 16.
2. **New → Web Service**: settings from section 3, environment variables
   from section 6, `DATABASE_URL` = the database's *Internal* URL.
3. (Option B only) **New → Static Site**: settings from section 4.

## 13. Automatic deploys from GitHub

`autoDeploy: true`: every push to the connected branch rebuilds and
redeploys. Render waits for `/api/health` to return 200 before switching
traffic to the new instance, so a release that fails to start never
replaces the running one. To pause deploys, set **Auto-Deploy → Off** in
the service settings.

## 14. Health check

```
curl https://<service>.onrender.com/api/health
# {"status":"ok","demo_mode":false,"llm_provider":"groq","llm_available":true,...}
```

`/api/health` is public and doesn't touch the database, so it reports
process liveness only. `llm_available` / `search_available` show whether
those keys are set. They never echo the keys.

## 15. Logs and troubleshooting

Service → **Logs**. Lines worth knowing:

| Log line | Meaning |
|---|---|
| `Running upgrade ... -> c2f4a7e91b3d` | migrations applied on startup |
| `Database schema is up to date (postgresql+psycopg://verifi:***@...)` | connected (password masked) |
| `Synced TCS: 6 listed, 6 new` | industry filings fetched from the exchange |
| `Startup complete. demo_mode=False ...` | ready |

| Symptom | Fix |
|---|---|
| Deploy hangs at startup, no "Startup complete" | `DATABASE_URL` wrong or the database is in another region. Use the *Internal* URL. |
| Instance restarts with "out of memory" | `RAG_ENABLED=true` on a 512 MB plan. Set it to `false` or upgrade. |
| Industry dashboard empty, sync errors in logs | The exchange API refused Render's IP. Copy data from local (section 8). |
| Google: "redirect_uri_mismatch" | The redirect URI in Google Cloud must equal `<APP_BASE_URL>/api/auth/google/callback`. |
| Magic link email not sent (502) | `RESEND_FROM_EMAIL` on `onboarding@resend.dev` only sends to your own Resend account email. Verify a domain in Resend. |
| Users logged out right after signing in (Option B) | Third-party cookie blocked (section 10). Use Option A or a shared custom domain. |
| First request after idle takes ~1 min | Free instances sleep after 15 min idle (section 19). |

## 16. Blockchain, simulation mode and wallets

This repository has **no blockchain, smart-contract, Hardhat or wallet
code**. Nothing in this deployment starts a local chain, holds a private
key, or signs transactions. The closest equivalent is `DEMO_MODE`, which
switches every external provider to clearly labelled sample data and needs
no credentials.

## 17. Sign-in integrations (the "wallet" equivalent)

- Email + password and guest sessions: always on, no configuration.
- Google: `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` plus the redirect URI
  in section 11.
- Magic link: `RESEND_API_KEY` plus a verified sender domain for real users.
- Sessions are random tokens in an HttpOnly cookie. Only their SHA-256 is
  stored. Keys stay server-side.

## 18. LLM provider configuration

The AI features (query planning, claim extraction, verification, IPO
question answering) use `LLM_PROVIDER` with `GROQ_API_KEY` or
`OPENAI_API_KEY`, set **only** on the web service. With no key, the app
starts normally and the research pipeline runs in labelled demo mode. The
IPO question box shows the most relevant report excerpt instead of a
generated answer. Keys are never logged or returned by the API.

## 19. Free-tier limits and costs

| Resource | Free plan | Consequence |
|---|---|---|
| Web service | 512 MB RAM, sleeps after 15 min idle, ~1 min cold start | Keep `RAG_ENABLED=false`. Long IPO reports then use prefix truncation instead of semantic retrieval. |
| PostgreSQL | 1 GB, **expires 30 days after creation** | Upgrade to a paid database (from ~$7/month) before day 30, or the data is deleted. |
| Build minutes | limited per month | Each push rebuilds the Docker image. |

To run with semantic retrieval, use a **Standard** web service (2 GB) and
set `RAG_ENABLED=true`. The embedding model (~90 MB) downloads on first
use and loads in the background at startup. Provider APIs (Groq, SerpAPI,
Alpha Vantage, Resend) have their own free quotas.

## 20. Safe redeploys and rollback

- Every deploy is health-checked before traffic switches, so a broken
  start is never promoted.
- **Rollback**: service → **Events** → pick an earlier successful deploy
  → **Rollback**.
- Migrations only move forward. Before deploying a migration that alters
  or drops columns, take a backup (paid databases have daily backups, or
  `pg_dump` with the External URL) and make the change additive where
  possible.
- Rotate a leaked key by updating it in **Environment** (this triggers a
  redeploy). Never commit keys to the repository.

---

## Deployment checklist

- [ ] Code (with `render.yaml`, `Dockerfile`, `.dockerignore`) pushed to GitHub
- [ ] Render → New → Blueprint → repository selected
- [ ] Secrets entered: at least `GROQ_API_KEY`. Optionally `SERPAPI_API_KEY`, `ALPHAVANTAGE_API_KEY`, `SEC_EDGAR_USER_AGENT`, Google, Resend
- [ ] Deploy finished. `/api/health` returns `{"status":"ok"}`
- [ ] Logs show the migrations and "Startup complete"
- [ ] Industry dashboard shows the ten companies (or copy data from local)
- [ ] `python -m scripts.seed_ipo` run against the Render database
- [ ] Google redirect URI added and test users configured (if using Google)
- [ ] Sign in, guest session, research, IPO question box checked in the browser
- [ ] Calendar reminder: upgrade the free database before day 30
