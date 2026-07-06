# Implementation Guide — AI-Spaces

This document explains the technologies used in the project, why they are needed, how the project is structured, and how all the pieces connect.

---

## 1. What You Need to Install

You need four things installed on your computer. Everything else runs inside Docker containers.

### 1.1 Git

Version control — tracks every change and lets the team work on the same code without overwriting each other's work.

Download: https://git-scm.com/downloads

```bash
git --version
```

### 1.2 Docker Desktop

Docker lets you run applications inside isolated containers. Instead of installing PostgreSQL, Keycloak, etc. directly on your machine, each service runs in its own container. Docker Desktop includes both the Docker engine and Docker Compose, which starts multiple containers together with one command.

Download: https://www.docker.com/products/docker-desktop/

Make sure Docker Desktop is running, then verify:

```bash
docker --version
docker compose version
```

### 1.3 Node.js (v20 or later)

Needed to install frontend packages and run the Vite dev server locally.

Download: https://nodejs.org/ (LTS version)

```bash
node --version
npm --version
```

### 1.4 Python (3.12 or later)

The backend and orchestrator are written in Python. Needed for running them locally, running tests, and using the Alembic migration tool.

Download: https://www.python.org/downloads/

```bash
python --version
```

---

## 2. Technologies Used and Why

### 2.1 Frontend — React + Vite (TypeScript)

| Component | Purpose |
|---|---|
| React | JavaScript library for building the UI from reusable components |
| Vite | Build tool with fast hot reload during development |
| TypeScript | Typed JavaScript — catches errors before runtime, better editor support |

During development the frontend runs on your machine via `npm run dev` (port 5173). In production it is built into static files and served by Nginx inside a Docker container.

### 2.2 Backend — FastAPI (Python)

| Component | Purpose |
|---|---|
| FastAPI | Python web framework for the REST API; generates Swagger docs automatically at `/docs` |
| Uvicorn | ASGI server that runs FastAPI |
| SQLAlchemy | ORM — interact with PostgreSQL using Python objects instead of raw SQL |
| Alembic | Database migration tool — applies schema changes without losing data |

During development the backend runs locally via `uvicorn app.main:app --reload` (port 8000). In production it runs inside a Docker container.

### 2.3 Database — PostgreSQL

Stores all application state: spaces, jobs, users, and artifact metadata. The backend accesses it via SQLAlchemy. PostgreSQL always runs inside a Docker container — you never install it on your machine directly.

Main tables:

- `spaces` — one row per registered AI Space (name, container image, input/output types, status)
- `jobs` — one row per submitted job (status, progress, artifact paths, timestamps)
- `users` — one row per logged-in user (created automatically on first login)
- `artifacts` — one row per output file produced by a job

### 2.4 Auth — Keycloak

Keycloak is an open-source identity provider. Users log in through Keycloak (OIDC / Authorization Code + PKCE flow). The browser receives a JWT token and sends it with every API request. The backend validates the token signature against Keycloak's public keys.

Three roles are defined in the `ai-spaces` realm:

- `end_user` — can browse spaces and submit jobs
- `space_creator` — can also create and publish spaces
- `admin` — full access including user management

### 2.5 Orchestrator

A separate Python service that polls the backend for queued jobs and starts a Kubernetes Job for each one. The runner container (e.g. `ai-spaces-acestep-mock:dev`) fetches its input from the backend, processes it, uploads the result, and then marks the job as succeeded or failed.

### 2.6 Kubernetes / kind

Each AI job runs as an isolated Kubernetes Job pod. For local development we use kind (Kubernetes in Docker), which creates a full cluster inside Docker Desktop. The automated setup script (`scripts/setup-kind.sh`) handles the entire local cluster setup.

---

## 3. Project Structure

```
apps/
  backend/        FastAPI backend, Alembic migrations, tests
  frontend/       React frontend
  orchestrator/   Job orchestrator
  acestep-runner/ ACE-Step 1.5 runner (text -> music)
  sam3d-runner/   SAM 3D Objects runner (image -> GLB)
infra/
  k8s/            Kubernetes manifests (namespace, postgres, backend, etc.)
  kind/           kind cluster config
docs/
  implementation-guide.md   This file
  test-results.md           Test report
scripts/
  setup-kind.sh   Automated kind cluster setup
docker-compose.yml
.env.example
```

---

## 4. How the Services Connect

```
Browser
  |
  | OIDC login
  v
Keycloak (port 8080)

Browser
  |
  | HTTP + JWT
  v
Frontend (port 5173)
  |
  | REST API calls
  v
Backend (port 8000)
  |                    \
  | SQLAlchemy          | artifact files
  v                     v
PostgreSQL           /app/storage (volume)
                          ^
Orchestrator              | reads/writes
  |                       |
  | creates K8s Job       |
  v                       |
Runner pod ---------------+
  (e.g. acestep-mock)
```

When you run `docker compose up`, Postgres, Keycloak, the backend and the orchestrator start together. The frontend runs separately with `npm run dev`. In the Kubernetes setup, everything runs in the `ai-spaces` namespace.

---

## 5. How a Job Flows Through the System

1. User opens the Space Hub, picks a space and fills in the input form.
2. Frontend sends the input to `POST /spaces/{id}/jobs` as multipart form data.
3. Backend creates a job row with status `QUEUED` and returns the job ID.
4. Frontend navigates to the job detail page and polls for status updates every 2 seconds.
5. Orchestrator picks up the queued job and creates a Kubernetes Job with the space's container image.
6. Runner container starts, fetches its input from `GET /internal/jobs/{id}/runner-input`.
7. Runner reports progress via `PATCH /internal/jobs/{id}/progress`.
8. Runner uploads its output file to `POST /internal/jobs/{id}/artifacts`.
9. Runner calls `PATCH /internal/jobs/{id}/succeed` and exits.
10. Job detail page shows the result and offers a download link.

---

## 6. Environment Variables

Configuration is stored in `.env` (not committed to git). Copy `.env.example` to get started:

```bash
cp .env.example .env
```

Key variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (async driver) |
| `ALEMBIC_DATABASE_URL` | PostgreSQL connection string (sync driver, for migrations) |
| `AUTH_PROVIDER` | `dev` (no login needed) or `oidc` (full Keycloak login) |
| `OIDC_ISSUER` | Keycloak realm URL as seen by the browser |
| `OIDC_JWKS_URL` | Keycloak JWKS endpoint as seen by the backend container |
| `INTERNAL_SERVICE_TOKEN` | Shared secret between backend and orchestrator |

---

## 7. Useful Commands

```bash
# Start everything with Docker Compose
docker compose up

# Run backend tests (228 tests)
cd apps/backend
python -m pytest tests/ --cov=app --cov-branch -q

# Run frontend tests (24 tests)
cd apps/frontend
npm run test

# Apply database migrations
cd apps/backend
alembic upgrade head

# Full kind cluster setup (automated)
bash scripts/setup-kind.sh

# Check running pods in kind
kubectl get pods -n ai-spaces

# View logs from a service
docker compose logs backend --follow
kubectl logs -n ai-spaces deploy/orchestrator --follow

# Delete kind cluster
kind delete cluster --name ai-spaces
```

---

## 8. Runner Contract

Every AI Space is packaged as a Docker container that follows the same interface. This is what makes adding new spaces possible without changing the backend or frontend.

The orchestrator passes these environment variables to the runner container:

| Variable | Purpose |
|---|---|
| `JOB_ID` | ID of the job to process |
| `BACKEND_API_URL` | Backend base URL for internal API calls |
| `RUNNER_TOKEN` | Shared secret (same as `INTERNAL_SERVICE_TOKEN`) |

The runner must:

1. Call `GET /internal/jobs/{id}/runner-input` to fetch the input payload.
2. Process the input.
3. Report progress via `PATCH /internal/jobs/{id}/progress`.
4. Upload the result file to `POST /internal/jobs/{id}/artifacts`.
5. Call `PATCH /internal/jobs/{id}/succeed` on success or `PATCH /internal/jobs/{id}/fail` on error.
6. Exit with code 0.

See `runner-template/reference_runner.py` for a minimal example.
