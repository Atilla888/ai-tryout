# AI-Spaces-Tryout

Course project at Hof University. You pick a space, send input, wait while a job runs, then read or download the output.

This README explains how to run everything on your machine for Sprint 1: Postgres in Docker, the API, the orchestrator, the fake runner, and optionally the React UI. The curl section at the end walks through a full job from submit to result.

The backend lives in `apps/backend`. The orchestrator is `apps/orchestrator`; it watches for queued jobs and starts workers. Each worker is the fake runner in `apps/fake-runner`, which only pretends to run a model so we can test the pipeline before Kubernetes and real containers exist. The website is `apps/frontend` on port 5173 if you want a UI instead of curl.

You need Docker, Python 3.14+, and Node 20+ if you use the frontend. On Windows, use PowerShell for the commands below.

## First-time setup

Work from the repository root (where `docker-compose.yml` is).

Copy the environment file:

```powershell
copy .env.example .env
```

`INTERNAL_SERVICE_TOKEN` in `.env` must be the same value you pass to the orchestrator and the fake runner. For local work, `changeme-internal-token` is fine. `DATABASE_URL` should point at `localhost:5432` when Postgres runs in Docker on your machine.

Install Python dependencies:

```powershell
venv\Scripts\pip install -r apps\backend\requirements.txt
venv\Scripts\pip install -r apps\orchestrator\requirements.txt
```

If `venv` is only under `apps/backend`, use `..\..\venv\Scripts\pip` from there instead.

Start Postgres first (next section), then apply migrations:

```powershell
cd apps\backend
..\..\venv\Scripts\activate
alembic upgrade head
```

Jobs need a user row in the database. Run this once:

```powershell
docker compose exec -T postgres psql -U aispacesuser -d aispaces -c "INSERT INTO users (id, subject_id, idp, email, display_name, role) VALUES ('00000000-0000-0000-0000-000000000001', 'local-dev', 'local', 'dev@example.com', 'Dev User', 'user') ON CONFLICT (id) DO NOTHING;"
```

## Starting the services

Use separate terminal tabs and leave each server running.

**Postgres.** From the repo root:

```powershell
docker compose up -d postgres
```

**Backend** on port 8000:

```powershell
cd apps\backend
..\..\venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000
```

Check with `curl.exe http://127.0.0.1:8000/health` — you should see `{"status":"ok"}`. API docs are at http://127.0.0.1:8000/docs.

**Orchestrator.** It will not do anything useful until a job is queued.

```powershell
cd apps\orchestrator

$env:API_BASE_URL = "http://127.0.0.1:8000"
$env:INTERNAL_SERVICE_TOKEN = "changeme-internal-token"
$env:CONCURRENCY_LIMIT = "2"
$env:POLL_INTERVAL_SECONDS = "3"

..\..\venv\Scripts\python.exe main.py
```

When idle it polls every few seconds. After you submit a job you should see lines about starting the job and spawning the runner.

**Frontend (optional).**

```powershell
cd apps\frontend
npm install
npm run dev
```

Open http://localhost:5173. Set `VITE_API_URL=http://localhost:8000` in `.env` at the repo root.

Keep another terminal free for curl commands below.

## Testing with curl

Swagger can create spaces but not submit jobs — the job endpoint expects form data and does not show up properly in `/docs`. Use curl or the website to submit work.

Create a file `tmp-space.json` in the repo root:

```json
{
  "slug": "demo-space",
  "name": "Demo Space",
  "description": "Local test",
  "task_type": "Text",
  "input_types": ["text"],
  "output_types": ["text"],
  "container_image": "fake:latest",
  "ui_config": {
    "inputs": [
      {
        "name": "prompt",
        "type": "text",
        "label": "Prompt",
        "required": true
      }
    ]
  },
  "runner_config": {},
  "visibility": "PUBLIC",
  "status": "PUBLISHED"
}
```

Create the space:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/spaces" -H "Content-Type: application/json" -d "@tmp-space.json"
```

Copy the `id` from the response — that is your space id.

Submit a job (replace the uuid in the URL):

```powershell
curl.exe -X POST "http://127.0.0.1:8000/spaces/SPACE_ID/jobs" -F "prompt=hello test" 
```

The `-F` part is required. Without it you get `Job input is required`. Copy the job `id` from the response. Status should be `QUEUED`. Within a few seconds the orchestrator should pick it up.

Poll the job (replace `JOB_ID`):

```powershell
curl.exe http://127.0.0.1:8000/jobs/JOB_ID
```

Run that again every couple of seconds. You will usually see `QUEUED`, then `STARTING`, then `RUNNING` with rising progress, then `SUCCEEDED` after about fifteen seconds.

To list output files:

```powershell
curl.exe http://127.0.0.1:8000/jobs/JOB_ID/artifacts
```

Open `http://127.0.0.1:8000/artifacts/ARTIFACT_ID/preview` in a browser to read the dummy text file.

## Stopping

Stop the frontend and orchestrator with Ctrl+C, then the backend, then run `docker compose stop postgres` from the repo root.

## Backend tests

```powershell
cd apps\backend
..\..\venv\Scripts\pytest tests\ -v
```

## Configuration

See `.env.example` for database URLs, tokens, and storage paths. When the API runs on your laptop, use `localhost` in `DATABASE_URL`, not the hostname `postgres` (that name is for containers talking to each other).

## When something breaks

If job submit says `Job input is required`, add `-F "prompt=hello test"` to the curl command.

If the orchestrator only prints `GET ... QUEUED` and never starts a job, make sure the job was actually created (`curl .../jobs?status=QUEUED`) and that the backend token matches `.env`.

`401` on internal routes means `INTERNAL_SERVICE_TOKEN` is wrong or missing.

If `health-db` fails, Postgres is not running.

If `/docs` only shows a handful of routes and version `0.1.0`, something else is still bound to port 8000 — stop old uvicorn processes and start the backend again.

Foreign key errors on submit usually mean the dev user insert above was skipped.
