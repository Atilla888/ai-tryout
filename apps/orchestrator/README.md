# Orchestrator

Small Python process for Sprint 1. It asks the backend for queued jobs, marks one as starting, and runs `apps/fake-runner/fake_runner.py` as a subprocess. By default it runs at most two jobs at the same time.

You need the API up, migrations applied, and the same `INTERNAL_SERVICE_TOKEN` as in `.env`.

Settings you can pass as environment variables: `API_BASE_URL` (defaults to `http://localhost:8000`), `INTERNAL_SERVICE_TOKEN` (required), `CONCURRENCY_LIMIT` (default 2), `POLL_INTERVAL_SECONDS` (default 3), and optionally `RUNNER_SCRIPT` if the fake runner lives somewhere else.

```powershell
cd apps/orchestrator
pip install -r requirements.txt

$env:API_BASE_URL = "http://127.0.0.1:8000"
$env:INTERNAL_SERVICE_TOKEN = "changeme-internal-token"

python main.py
```

From the repo root you can also run `python apps/orchestrator/main.py` with the same variables set.

Every few seconds it checks for finished subprocesses and looks for new queued work. For each job it calls the internal start endpoint, spawns the runner with `JOB_ID` and the token, and marks the job failed if the process exits with an error while the job is still active.

The full walkthrough (Postgres, backend, curl submit) is in the root `README.md`.
