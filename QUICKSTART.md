# AI-Spaces — Quick Start (everything already installed)

This guide is for anyone who has already set the project up once on their laptop
(Docker, the Python `venv`, and `npm install` are done). It shows the commands
you run **every time** you want to start the app. No setup steps here.

If this is your very first time on this machine, do the one-time setup in
[RUN_CHEATSHEET.md](RUN_CHEATSHEET.md) first.

---

## Why 4 terminals?

The app is made of separate programs that all need to run **at the same time**.
Each one has to keep running and "hold" its terminal window (it prints logs and
won't give the prompt back). So you open **one terminal tab per program** and
just leave it running.

| Terminal | Program | What it does |
|----------|---------|--------------|
| 1 | Postgres (in Docker) | The database |
| 2 | Backend | The API on port 8000 |
| 3 | Orchestrator | Runs the jobs you submit *(optional)* |
| 4 | Frontend | The website on port 5173 |

> **Tip:** In Windows Terminal, press `Ctrl` + `Shift` + `T` to open a new tab.
> Each tab should start in the project root
> (`...\Git_repo`). If not, `cd` into it first.

For just clicking around the website you only need terminals **1, 2, and 4**.
Add terminal **3** only when you want submitted jobs to actually run.

---

## The commands

### 🖥️ Terminal 1 — Database

Run from the project root:

```powershell
docker compose up -d postgres
```

This one returns the prompt right away (Docker runs it in the background). You
can leave the tab or reuse it.

### 🖥️ Terminal 2 — Backend (port 8000)

```powershell
cd apps\backend
..\..\venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000
```

Leave this running. It keeps printing logs — that's normal.

### 🖥️ Terminal 3 — Orchestrator (optional — only for running jobs)

```powershell
cd apps\orchestrator
$env:API_BASE_URL = "http://127.0.0.1:8000"
$env:INTERNAL_SERVICE_TOKEN = "changeme-internal-token"
$env:CONCURRENCY_LIMIT = "2"
$env:POLL_INTERVAL_SECONDS = "3"
..\..\venv\Scripts\python.exe main.py
```

Leave this running too. When idle it just polls every few seconds.

### 🖥️ Terminal 4 — Frontend (the website)

```powershell
cd apps\frontend
npm run dev
```

Leave it running, then open **http://localhost:5173** in your browser. 🎉

---

## Is it working?

In any spare terminal:

```powershell
curl.exe http://127.0.0.1:8000/health
```

You should see:

```json
{"status":"ok"}
```

If yes, the backend is up. Then just open http://localhost:5173.

---

## How to stop

Go to each running terminal and press **`Ctrl` + `C`**. Do it in this order:

1. Frontend (Terminal 4)
2. Orchestrator (Terminal 3)
3. Backend (Terminal 2)

Then stop the database from the project root:

```powershell
docker compose stop postgres
```

---

## If something goes wrong

| Problem | What to do |
|---------|-----------|
| Backend seems stuck / can't reach the database | Open `.env` and change `DATABASE_URL` host from `localhost` to `127.0.0.1` (a Windows quirk on this setup) |
| Website loads but data won't save/load | Make sure Terminal 2 (backend) is still running |
| Submitted a job but nothing happens | Terminal 3 (orchestrator) isn't running — start it |
| `Ctrl + C` doesn't stop it | Close the terminal tab |

Full details and one-time setup are in [RUN_CHEATSHEET.md](RUN_CHEATSHEET.md).
