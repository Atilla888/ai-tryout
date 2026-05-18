# AI-Spaces-Tryout

> A Hof University platform where users can browse AI spaces, submit input through browser UIs, run AI model containers on demand in Kubernetes, track progress, preview results, and download generated files.

Inspired by [Hugging Face Spaces](https://huggingface.co/spaces), this platform is scoped and adapted for Hof University infrastructure.

---

## What It Does

1. A user opens the platform and sees available AI spaces (model cards).
2. The user selects a space and fills in an input form rendered from configuration.
3. The platform creates an asynchronous job and shows queue position.
4. The orchestrator picks the job and starts a model container in Kubernetes.
5. The model reports progress back to the backend.
6. On completion the user previews the result in the browser, downloads the output, and receives a browser notification.
7. The user can revisit their private job history for up to 14 days.

---

## Repository Layout

```
.
├── apps/
│   ├── frontend/           # React + TypeScript + Vite SPA
│   ├── backend-api/        # FastAPI REST backend
│   └── orchestrator/       # Job orchestrator service (Kubernetes-aware)
├── models/
│   ├── common-runner-template/   # Reference model runner contract & template
│   ├── object-detection-space/   # YOLO-based object detection model runner
│   ├── audio-space/              # Audio model runner (speech-to-text / TTS)
│   └── video-or-3d-space/        # Video / 3D generation model runner
├── infra/
│   ├── docker/             # Shared Dockerfile snippets / base images
│   ├── k8s/                # Kubernetes manifests (Jobs, Deployments, Services)
│   └── scripts/            # Helper scripts (seed data, cleanup, deploy)
├── tests/
│   └── e2e/                # End-to-end tests (Playwright or similar)
├── docs/                   # Project documentation (see docs/README.md)
│   └── wireframes/         # Early static HTML prototypes
├── .env.example            # All required environment variables (no secrets)
├── .gitlab-ci.yml          # CI pipeline (lint)
└── docker-compose.yml      # Local development stack
```

---

## Quick Start (Local Development)

### Prerequisites

| Tool | Minimum Version |
|------|----------------|
| Docker + Docker Compose | Docker 24+ |
| Node.js | 20 LTS |
| Python | 3.11+ |
| Git | any recent |

### 1. Clone the repository

```bash
git clone https://gitlab.hof-university.de/atilla888/ai-spaces.git
cd ai-spaces
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env only if you need non-default ports or credentials
```

**Never commit the `.env` file.** It is listed in `.gitignore`.

### 3. Start the full stack

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend (dev server) | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Backend Swagger docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

### 4. Run the backend in isolation (no Docker)

```bash
cd apps/backend-api
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### 5. Run the frontend in isolation (no Docker)

```bash
cd apps/frontend
npm install
npm run dev
```

---

## Running Tests

### Backend unit tests

```bash
cd apps/backend-api
pytest tests/unit/
```

### Backend integration tests

```bash
pytest tests/integration/
```

### End-to-end tests

```bash
cd tests/e2e
npm install
npx playwright test
```

### Lint

```bash
# Python
cd apps/backend-api && ruff check .

# TypeScript / Frontend
cd apps/frontend && npm run lint
```

---

## Architecture

**High-level flow:**

```
Browser → Backend API → PostgreSQL (job queue)
                      ↓
              Orchestrator Service
                      ↓
             Kubernetes Cluster
                      ↓
           Model Runner Container
                      ↓
       Backend API + Persistent Storage
```

---

## Environment Variables

All variables are documented in [`.env.example`](.env.example). Required variables:

| Variable | Description |
|----------|-------------|
| `POSTGRES_USER` | Database user |
| `POSTGRES_PASSWORD` | Database password (use a strong value in production) |
| `POSTGRES_DB` | Database name |
| `DATABASE_URL` | Full SQLAlchemy async connection string |
| `SECRET_KEY` | Backend secret key for token signing |
| `STORAGE_PATH` | Filesystem path where artifacts are persisted |
| `VITE_API_BASE_URL` | Backend API base URL used by the frontend |


---

## Team

Hof University of Applied Sciences — Interdisciplinary Software Development Project  
Course topic: Hugging Face Spaces for Hof University / AI-Spaces-Tryout
