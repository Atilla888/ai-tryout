# AI-Spaces

A platform for running AI model jobs through a web UI. Users pick a Space (an AI model), submit inputs, and get results back — text, audio, or 3D models — without writing any code.

Built at Hof University of Applied Sciences, SS 2026.

## What it does

- **Space Hub** — browse and submit jobs to published AI Spaces
- **Job tracking** — live progress updates, artifact download
- **Creator dashboard** — define and publish new Spaces with custom input forms
- **Admin dashboard** — manage all Spaces and users
- **Kubernetes-native** — each job runs as an isolated K8s Job pod

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite |
| Backend | FastAPI (Python), PostgreSQL, SQLAlchemy |
| Auth | Keycloak (OIDC / JWT) |
| Orchestration | Custom Python orchestrator + Kubernetes Jobs |
| Infrastructure | Kubernetes (kind for local), Docker Compose (local dev) |

## Running locally

Two ways — pick one:

**Docker Compose** (fastest, 5 minutes):
```bash
cp .env.example .env
docker compose up
```
→ See [QUICKSTART.md](QUICKSTART.md) for the full walkthrough.

**Kubernetes with kind** (full stack):
```bash
bash scripts/setup-kind.sh
```
→ See [QUICKSTART.md](QUICKSTART.md#path-b-kubernetes-with-kind) for details.

## Project structure

```
apps/
  backend/        FastAPI backend + Alembic migrations
  frontend/       React frontend
  orchestrator/   Job orchestrator (subprocess or K8s backend)
  sam3d-runner/   SAM 3D Objects runner (image → GLB)
  acestep-runner/ ACE-Step 1.5 runner (text → music)
infra/
  k8s/            Kubernetes manifests
  kind/           kind cluster config
docs/
  QUICKSTART_MAC.md   Mac-specific local dev guide
  test-results.md     Test protocol (unit, load, manual)
scripts/
  setup-kind.sh   Automated kind cluster setup
```

## Included AI Spaces (mock mode, no GPU needed)

| Space | Input | Output |
|---|---|---|
| ACE-Step 1.5 — Text to Music | Text prompt | WAV audio |
| 3D Generator — SAM 3D Objects | Image upload | GLB 3D model |

## Tests

```bash
# Backend (228 tests, 80% branch coverage)
cd apps/backend
python -m pytest tests/ --cov=app --cov-branch -q

# Frontend (24 tests)
cd apps/frontend
npm run test
```

Full test results: [docs/test-results.md](docs/test-results.md)
