# Orchestrator

Polls the backend internal API for queued jobs, marks one as starting, and runs a model runner script as a subprocess.

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_BASE_URL` | no | `http://localhost:8000` | Backend base URL |
| `INTERNAL_SERVICE_TOKEN` | yes | — | Must match backend `INTERNAL_SERVICE_TOKEN` |
| `RUNNER_SCRIPT` | yes | — | Path to the model runner Python script |
| `CONCURRENCY_LIMIT` | no | `2` | Max simultaneous jobs |
| `POLL_INTERVAL_SECONDS` | no | `3` | Poll interval in seconds |

The runner subprocess receives `JOB_ID` (internal integer id), `API_BASE_URL`, and `INTERNAL_SERVICE_TOKEN`.
