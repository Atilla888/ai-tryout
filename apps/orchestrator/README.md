# Orchestrator

Polls the backend internal API for queued jobs, claims them, and runs a model
runner through a **runner backend**. It also drives real cancellation: when a job
is `CANCELLING` it terminates the worker and finalizes the job to `CANCELLED`.

## Runner backends

Select with `RUNNER_BACKEND`:

| Backend | What it does | When to use |
|---------|--------------|-------------|
| `subprocess` (default) | Runs `RUNNER_SCRIPT` as a local child process | Local dev, tests, no cluster |
| `kubernetes` | Creates one Kubernetes Job per platform job from the space's `container_image` | Real execution on the cluster |

For every job the orchestrator fetches `GET /internal/jobs/{id}/execution-data`
(runner image, space id, input reference) and passes the runtime values to the
worker through environment variables (see the runner contract in
[`../../runner-template/README.md`](../../runner-template/README.md)).

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_BASE_URL` | no | `http://localhost:8000` | Backend base URL |
| `INTERNAL_SERVICE_TOKEN` | yes | — | Must match backend `INTERNAL_SERVICE_TOKEN` |
| `RUNNER_BACKEND` | no | `subprocess` | `subprocess` or `kubernetes` |
| `RUNNER_SCRIPT` | only for `subprocess` | — | Path to the model runner Python script |
| `K8S_NAMESPACE` | only for `kubernetes` | `default` | Namespace the runner Jobs are created in |
| `CONCURRENCY_LIMIT` | no | `2` | Max simultaneous jobs |
| `POLL_INTERVAL_SECONDS` | no | `3` | Poll interval in seconds |

The runner receives `JOB_ID`, `SPACE_ID`, `BACKEND_API_URL` (and `API_BASE_URL`),
`RUNNER_TOKEN` (and `INTERNAL_SERVICE_TOKEN`), and `INPUT_REFERENCE`.

## Local run (subprocess backend)

```bash
export INTERNAL_SERVICE_TOKEN=changeme-internal-token
export RUNNER_SCRIPT=$(pwd)/fake_runner.py
python main.py
```

`fake_runner.py` is a self-contained reference worker: it fetches its input
(including uploaded INPUT files), reports progress, uploads a result artifact, and
reports success. The Kubernetes backend requires `kubernetes` RBAC to create,
read, and delete Jobs in `K8S_NAMESPACE`.
