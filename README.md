# AI-Spaces

A platform for running AI model jobs through a web interface. Users pick a Space (an AI model), fill in their inputs, and get results back — text, audio, or 3D models — without writing any code.

Created as part of the interdisciplinary software engineering project at Hof University of Applied Sciences, SS 2026.

## Overview

Users can browse Spaces and submit jobs. Each job runs in its own Kubernetes pod and produces artifacts that can be previewed or downloaded directly in the app. Space creators can define their own Spaces with custom input forms and publish them. Admins have a dashboard to manage all Spaces and users.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite |
| Backend | FastAPI, PostgreSQL, SQLAlchemy |
| Auth | Keycloak (OIDC / JWT) |
| Orchestration | Python orchestrator + Kubernetes Jobs |
| Infrastructure | Kubernetes (kind locally), Docker Compose |

## Running locally

There are two options:

Docker Compose (easiest, about 5 minutes):
```bash
cp .env.example .env
docker compose up
```

Kubernetes with kind (full stack):
```bash
bash scripts/setup-kind.sh
```

See [QUICKSTART.md](QUICKSTART.md) for details.

## Project structure

```
apps/
  backend/        FastAPI backend + Alembic migrations
  frontend/       React frontend
  orchestrator/   Job orchestrator (subprocess or K8s)
  sam3d-runner/   SAM 3D Objects runner (image -> GLB)
  acestep-runner/ ACE-Step 1.5 runner (text -> music)
infra/
  k8s/            Kubernetes manifests
  kind/           kind cluster config
docs/
  test-results.md     Test report (unit, load, manual)
scripts/
  setup-kind.sh   Automated kind cluster setup
```

## Included AI Spaces (mock mode, no GPU required)

| Space | Input | Output |
|---|---|---|
| ACE-Step 1.5 – Text to Music | Text prompt | WAV audio file |
| 3D Generator – SAM 3D Objects | Image upload | GLB 3D model |

## Running the tests

```bash
# Backend (228 tests, 80% branch coverage)
cd apps/backend
python -m pytest tests/ --cov=app --cov-branch -q

# Frontend (24 tests)
cd apps/frontend
npm run test
```

Full test results: [docs/test-results.md](docs/test-results.md)
