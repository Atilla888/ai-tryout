# AI-Spaces-Tryout

A project inspired by [Hugging Face Spaces](https://huggingface.co/spaces): a place where people can discover AI “spaces”, submit inputs through a web UI, run model workloads, follow job progress, and collect results.

## What you can do with it

Someone opens the platform, picks a space, and fills in a form driven by that space’s configuration. The backend records an asynchronous job and exposes status (including queue position when relevant). An orchestrator is meant to start the right model workload in Kubernetes; the runner reports progress back to the API. When a job finishes, the user can preview output in the browser, download artifacts, and look back at recent history.

## Getting started locally

You need Docker with Compose, Git, and—for working on the apps directly—Node.js 20+ and Python 3.14+.

Clone the repository and copy the example environment file:

```bash
git clone https://gitlab.hof-university.de/atilla888/ai-spaces.git
cd ai-spaces
cp .env.example .env
```

Copy `.env.example` to `.env` before the first `docker compose up` if you want custom secrets; Compose also works without `.env` using the defaults in `docker-compose.yml`.

Start PostgreSQL and the API with Docker:

```bash
docker compose up --build
```

With the default setup you get the API at [http://localhost:8000](http://localhost:8000) (OpenAPI docs at `/docs`) and PostgreSQL on port 5432.

### Running the backend without Docker

```bash
cd apps/backend
python3.14 -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Apply database migrations with Alembic when you need a fresh schema (`alembic upgrade head` from `apps/backend`).

### Running the frontend without Docker

```bash
cd apps/frontend
npm install
npm run dev
```

The Vite dev server usually serves the UI at [http://localhost:5173](http://localhost:5173). Point `VITE_API_URL` in `.env` at your backend if it is not on `http://localhost:8000`.

## Tests and lint

Backend integration tests (artifact upload, preview, download, list):

```bash
cd apps/backend
pip install -r requirements.txt
pytest tests/ -v
```

From `apps/frontend`, run `npm run lint` when working on the UI.

## How the pieces fit together

The browser talks to the FastAPI backend, which persists jobs and metadata in PostgreSQL. A separate orchestrator service will claim queued work and start model runners on Kubernetes. Runners call internal API endpoints to update progress and register artifacts; files land in configured storage. 

## Configuration

See [`.env.example`](.env.example) for database URLs, `SECRET_KEY`, `ARTIFACT_STORAGE_ROOT`, `INTERNAL_SERVICE_TOKEN`, and `VITE_API_URL`. Docker Compose overrides database hostnames to `postgres` inside containers; keep `localhost` in `.env` when running the API on your machine. Use strong secrets outside local development.

## Team

Hof University of Applied Sciences —> Interdisciplinary Software Development  
Course project: AI Spaces tryout for Hof University
