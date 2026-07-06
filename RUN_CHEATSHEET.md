# AI-Spaces — Start-It-Yourself Cheatsheet (Windows / PowerShell)

The app has 4 parts:

- **Postgres** — the database (Docker)
- **Backend** — FastAPI, port 8000
- **Orchestrator** — picks up queued jobs and runs the fake runner
- **Frontend** — React/Vite, port 5173

Keycloak (port 8080) is only needed if you want real login instead of dev mode.

---

## ⚠️ The one Windows gotcha

On this machine `localhost` resolves to IPv6 `::1`, and Docker drops those
connections to mapped container ports. **Use `127.0.0.1` for anything hitting a
Docker port** (Postgres, Keycloak). Native servers (Vite on `localhost:5173`)
are fine.

Your `.env` has `DATABASE_URL=...@localhost:5432`. If the backend hangs on DB
connect, change that host to `127.0.0.1`.

---

## Recommended path: hybrid dev (Postgres in Docker, rest native, no Keycloak)

This is the config that reliably works. `AUTH_PROVIDER=dev` in `.env` means the
backend treats every request as admin, so **no Keycloak is needed**.

Use a separate PowerShell tab per service and leave each one running.

### 0. One-time setup (skip if already done)

```powershell
# from repo root
copy .env.example .env          # only if .env doesn't exist yet
docker compose up -d postgres   # start DB
cd apps\backend
..\..\venv\Scripts\activate
alembic upgrade head            # apply migrations
```

### 1. Postgres (repo root)

```powershell
docker compose up -d postgres
```

### 2. Backend — port 8000

```powershell
cd apps\backend
..\..\venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000
```

Check: `curl.exe http://127.0.0.1:8000/health` → `{"status":"ok"}`
Docs: http://127.0.0.1:8000/docs

### 3. Orchestrator (only needed if you submit jobs)

```powershell
cd apps\orchestrator
$env:API_BASE_URL = "http://127.0.0.1:8000"
$env:INTERNAL_SERVICE_TOKEN = "changeme-internal-token"
$env:CONCURRENCY_LIMIT = "2"
$env:POLL_INTERVAL_SECONDS = "3"
..\..\venv\Scripts\python.exe main.py
```

### 4. Frontend — http://localhost:5173

```powershell
cd apps\frontend
npm install        # first time only
npm run dev
```

Open the app at **http://localhost:5173** (keep `localhost` here — Keycloak's
redirect whitelist expects it).

### Stop

Ctrl+C the frontend, orchestrator, backend (in that order), then:

```powershell
docker compose stop postgres
```

---

## Alternative: everything in Docker

Runs Postgres + Keycloak + Backend + Orchestrator in containers. The backend
here uses `AUTH_PROVIDER=oidc`, so you'll need to log in via Keycloak.

```powershell
# from repo root
docker compose up -d --build
```

Then run the frontend natively (step 4 above).
Keycloak admin: `admin` / `admin123` in the `ai-spaces` realm.

Stop everything:

```powershell
docker compose down        # add -v to also wipe the DB + Keycloak volumes
```

---

## Quick smoke test (curl)

```powershell
curl.exe http://127.0.0.1:8000/health
# submit a job to a space (needs a space id + orchestrator running):
curl.exe -X POST "http://127.0.0.1:8000/spaces/SPACE_ID/jobs" -F "prompt=hello test"
curl.exe http://127.0.0.1:8000/jobs/JOB_ID   # poll: QUEUED -> STARTING -> RUNNING -> SUCCEEDED
```

---

## When something breaks

| Symptom | Fix |
|---|---|
| Backend hangs connecting to DB | Change `DATABASE_URL` host from `localhost` -> `127.0.0.1` |
| `Job input is required` | Add `-F "prompt=..."` to the submit curl |
| Orchestrator never starts jobs | Check `INTERNAL_SERVICE_TOKEN` matches `.env` |
| `401` on internal routes | Wrong/missing `INTERNAL_SERVICE_TOKEN` |
| `/docs` shows only a few routes | Old uvicorn still on port 8000 — kill it and restart |
| FK error on job submit | Dev user row missing — re-run the `INSERT INTO users...` from README |

---

## Notes

- The `venv` path above (`..\..\venv\`) matches the README. If that folder is
  missing, there's also one at `apps\backend\.venv`.
- Backend tests run separately: from `apps\backend`, run
  `..\..\venv\Scripts\pytest tests\ -v`.
