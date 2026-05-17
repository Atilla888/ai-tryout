---
name: Step-by-step Build Order
overview: A sequential step-by-step plan to build the AI Spaces platform from zero to a working MVP, ordered so that each step produces something visible and testable.
todos:
  - id: step01
    content: "Step 1: Project skeleton and Git setup"
    status: pending
  - id: step02
    content: "Step 2: Docker Compose with PostgreSQL, pgAdmin, MinIO"
    status: pending
  - id: step03
    content: "Step 3: Backend skeleton (FastAPI + DB tables + GET /api/models)"
    status: pending
  - id: step04
    content: "Step 4: Frontend skeleton (React + Vite + Tailwind + landing page with model cards)"
    status: pending
  - id: step05
    content: "Step 5: Model page with description and file upload UI"
    status: pending
  - id: step06
    content: "Step 6: Backend POST /api/requests + GET /api/requests/:id endpoints"
    status: pending
  - id: step07
    content: "Step 7: Wire frontend Generate button to backend"
    status: pending
  - id: step08
    content: "Step 8: YOLO v11 model container (Dockerfile + inference.py)"
    status: pending
  - id: step09
    content: "Step 9: Kubernetes Job orchestration from backend"
    status: pending
  - id: step10
    content: "Step 10: Full end-to-end flow in browser (MVP complete)"
    status: pending
  - id: step11
    content: "Step 11: Tests (unit + integration)"
    status: pending
  - id: step12
    content: "Step 12: Documentation and cleanup"
    status: pending
  - id: step13
    content: "Step 13 (Sprint 2): LTX 2.3 and SAM 3D model containers"
    status: pending
  - id: step14
    content: "Step 14 (Sprint 2): WebSocket, notifications, gallery, full K8s deployment"
    status: pending
isProject: false
---

# AI Spaces — Step-by-Step Build Order

Each step ends with something you can see or test. No step builds something that floats in the air waiting for other pieces.

## Step 1 — Project skeleton and Git setup

Create the folder structure, initialize Git, and create a `.gitignore`. No code yet — just the empty project scaffolding as described in [implementation-guide.md](docs/implementation-guide.md).

**What you have after this step**: a clean Git repo with the folder structure ready.

## Step 2 — Docker Compose with PostgreSQL and MinIO

Write a `docker-compose.yml` that starts PostgreSQL, pgAdmin, and MinIO. No backend or frontend yet — just the infrastructure services.

**What you have after this step**: `docker compose up` starts the database and file storage. You can open pgAdmin at `localhost:5050` and MinIO console at `localhost:9001` in your browser.

## Step 3 — Backend skeleton (FastAPI)

Create the FastAPI app with:

- A `/health` endpoint
- Database connection to PostgreSQL via SQLAlchemy
- The `models` and `requests` database tables
- A seed script that inserts the three AI models (YOLO v11, LTX 2.3, SAM 3D) into the `models` table
- A `GET /api/models` endpoint that returns the list of registered models
- Add the backend to Docker Compose

**What you have after this step**: open `localhost:8000/docs` (auto-generated Swagger UI), call `GET /api/models`, and see the three model definitions returned as JSON.

## Step 4 — Frontend skeleton (React + Vite + Tailwind)

Create the React app with:

- Vite + Tailwind CSS + TypeScript setup
- A landing page that calls `GET /api/models` and displays the results as model cards (name, description, input/output types)
- Clicking a card navigates to `/models/:id` (empty page for now)
- Add the frontend to Docker Compose

**What you have after this step**: open `localhost:3000`, see three model cards. Click one and navigate to its page (blank for now).

## Step 5 — Model page: description and file upload

Build the model page (`/models/:id`):

- Fetches model details from `GET /api/models/:id`
- Shows model name, description, accepted input types
- File input field and a "Generate" button (button doesn't do anything yet)
- Basic layout: input area at top, space below for progress and results

**What you have after this step**: click a model card, see its description and an upload form. Select a file — nothing happens yet when you click Generate, but the page is ready.

## Step 6 — Backend: request submission endpoint

Build the `POST /api/requests` endpoint:

- Accepts a file upload and a model ID
- Validates file type and size
- Uploads the file to MinIO (`inputs/{request_id}/filename`)
- Creates a row in the `requests` table with status `starting`
- Returns the `request_id`

Also build `GET /api/requests/:id` that returns the request status from the database.

**What you have after this step**: using Swagger UI or curl, you can submit a file, see it appear in MinIO (via the MinIO console), and check its status. No model execution yet — status stays at `starting`.

## Step 7 — Wire the frontend to request submission

Connect the model page's Generate button to `POST /api/requests`:

- Clicking Generate uploads the file and receives a `request_id`
- The page starts checking `GET /api/requests/:id` every few seconds
- Shows status text below the input area (starting → processing → completed/failed)

**What you have after this step**: click Generate, see "Starting..." appear on the page. Status stays at `starting` (no model runs yet), but the full frontend-to-backend-to-database-to-MinIO pipeline is working.

## Step 8 — YOLO v11 model container

Build the YOLO v11 container:

- `models/yolo-v11/Dockerfile` and `inference.py`
- Downloads input from MinIO, runs YOLO detection, uploads annotated image to MinIO
- Writes progress updates to MinIO (`progress/{request_id}.json`)
- Exits with code 0

Test it manually first: `docker build`, then `docker run` with env vars pointing to MinIO, verify the output appears in MinIO.

**What you have after this step**: a working YOLO container image that you can run manually and see results in MinIO console.

## Step 9 — Kubernetes Job orchestration

Build the backend orchestration service:

- Kubernetes Job manifest template (`k8s/model-job-template.yaml`)
- Backend code that creates a K8s Job when a request is submitted (using the `kubernetes` Python client)
- Backend monitors the Job status and updates the `requests` table
- Backend reads progress from MinIO and exposes it via `GET /api/requests/:id`

Enable Kubernetes in Docker Desktop if not already done. Create the project namespace.

**What you have after this step**: submit a request via Swagger UI → K8s Job starts → YOLO runs → result in MinIO → status updates to `completed`. Verify with `kubectl get jobs`.

## Step 10 — Full end-to-end flow in browser

Wire everything together:

- Frontend submits request → backend creates K8s Job → progress updates appear on the model page → result image appears inline with a download button
- Build the `GET /api/requests/:id/result` endpoint that fetches the result from MinIO and serves it

**What you have after this step**: open the browser, pick YOLO, upload an image, click Generate, watch progress, see the annotated result, download it. **This is the MVP.**

## Step 11 — Testing

- Backend unit tests: request lifecycle, MinIO operations, model registration
- One integration test: submit request → verify result file exists in MinIO
- Set up pytest with a test database

## Step 12 — Documentation and cleanup

- README with quick-start instructions
- Verify Docker Compose + Kubernetes setup works from a clean machine
- Clean up code, remove any hardcoded values, move secrets to `.env`

## Step 13 (Sprint 2) — Additional models

- LTX 2.3 container: `inference.py` calls Replicate/HuggingFace API, uploads MP4 result to MinIO
- SAM 3D container: `inference.py` calls cloud API, uploads GLTF result to MinIO
- Frontend: video player for LTX results, GLTF viewer for SAM results

## Step 14 (Sprint 2) — Enhancements

- Real-time progress via WebSocket
- Browser notifications on completion
- Gallery page
- Resource limit handling
- Full Kubernetes deployment (platform services in K8s too)

