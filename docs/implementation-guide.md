# Implementation Guide — AI Spaces for University

This document explains every technology used in the project, why it is needed, what you need to install on your machine, how the project is structured, and how all the pieces connect. It is written for team members who may not have used these tools before.

---

## 1. What You Need to Install on Your Machine

You need exactly **three things** installed on your computer. Everything else runs inside Docker containers.

### 1.1 Git

**What it is**: version control — tracks every change to the codebase and lets the team work on the same code without overwriting each other's work.

**Download**: https://git-scm.com/downloads

**Verify it works**:

```bash
git --version
```

### 1.2 Docker Desktop

**What it is**: Docker lets you run applications inside isolated "containers" — lightweight virtual machines that package an application with all its dependencies. Instead of installing Python, PostgreSQL, Node.js, Keycloak, etc. on your machine, each one runs in its own container. Docker Desktop includes both the Docker engine and Docker Compose.

**Why Docker Compose matters**: Docker Compose is a tool that starts multiple containers together with one command. Our project has several services (frontend, backend, database, file storage), and Docker Compose starts all of them with `docker compose up`.

**Download**: https://www.docker.com/products/docker-desktop/

After installation, make sure Docker Desktop is running (it sits in your system tray). Then verify:

```bash
docker --version
docker compose version
```

### 1.3 Node.js (v20 or later)

**What it is**: the JavaScript runtime used to develop the frontend locally. You need it to install frontend packages and run the development server on your machine (outside Docker, for faster iteration during development).

**Download**: https://nodejs.org/ (pick the LTS version)

**Verify it works**:

```bash
node --version
npm --version
```

### 1.4 Python (3.11 or later)

**What it is**: the language the backend is written in. You need it on your machine for running the backend locally during development, running tests, and using code editors with Python support.

**Download**: https://www.python.org/downloads/

**Verify it works**:

```bash
python --version
pip --version
```

---

## 2. Technologies Used and Why

Every technology in this project exists because it solves a specific problem. Nothing is here for decoration.

### 2.1 Frontend — React + Vite + Tailwind CSS (TypeScript)

| Component | What it does | Why we use it |
|---|---|---|
| **React** | A JavaScript library for building user interfaces by composing reusable components (buttons, forms, cards). | Most widely used UI library — large ecosystem, extensive documentation, and a skill that transfers to any future project. |
| **Vite** | A build tool that serves your React code during development with instant hot reload (you save a file, the browser updates immediately). | Much faster than older tools like Webpack. Zero configuration needed. |
| **Tailwind CSS** | A utility-first CSS framework — you style elements by adding class names like `bg-blue-500 text-white p-4` directly in your HTML. | Produces consistent, good-looking UIs fast without writing separate CSS files. |
| **TypeScript** | A typed version of JavaScript — catches errors before you run the code (e.g., passing a number where a string is expected). | Reduces bugs. Code editors provide better autocomplete and error detection. |

**Where it runs**: during development, on your machine via `npm run dev`. In production, it is built into static files and served from a Docker container (Nginx).

### 2.2 Backend — FastAPI (Python)

| Component | What it does | Why we use it |
|---|---|---|
| **FastAPI** | A Python web framework for building APIs (the backend endpoints that the frontend talks to). | Fast to develop, automatic API documentation (Swagger UI at `localhost:8000/docs`), built-in support for async operations and file uploads. |
| **Uvicorn** | The server that actually runs the FastAPI application. | The recommended server for FastAPI. Handles incoming HTTP requests and routes them to your code. |
| **SQLAlchemy** | A Python library that lets you interact with the PostgreSQL database using Python objects instead of writing raw SQL queries. | You write `request.status = "completed"` and SQLAlchemy translates it to the correct SQL statement. Reduces errors and makes database code readable. |
| **kubernetes Python client** | A Python library that talks to the Kubernetes API to create, monitor, and delete Jobs (short-lived containers) from your backend code. | This is how the backend starts a model container when a user submits a request. The same code works on a local cluster and in production. |

**Where it runs**: during development, on your machine via `uvicorn app.main:app --reload`. In production, inside a Docker container.

### 2.3 Database — PostgreSQL

**What it is**: a relational database server. It stores structured data in tables (rows and columns) and lets you query it ("give me all requests with status 'completed'").

**Why we need it**: when a user submits a request, the backend needs to track its state — which model was selected, what is the current status, where is the result file stored. This state must persist across server restarts and be accessible by multiple processes at the same time.

**What it stores**:

- **`models` table**: one row per registered AI model — name, description, Docker image name, input type, output type.
- **`requests` table**: one row per user request — request ID, which model, status (starting / processing / completed / failed), progress percentage, filesystem paths for input and output files, timestamps.

**How you interact with it**: your Python code uses SQLAlchemy. You never write SQL manually in normal development. For debugging, you use **pgAdmin** — a web UI that runs as a Docker container at `localhost:5050`, where you can browse tables, view rows, and run queries visually.

**Where it runs**: always inside a Docker container. You never install PostgreSQL on your machine.

### 2.4 File Storage — Filesystem (NFS)

**What it is**: artifact files (inputs uploaded by users and outputs produced by model containers) are stored on the host filesystem, mounted into the backend container as a Docker volume (`storage_data:/app/storage`). In a production Kubernetes deployment this volume is backed by an NFS share so every node can access the same files.

**Why not object storage (S3/MinIO)**: the current deployment uses a single-node setup where a shared volume is sufficient. Introducing an object storage service (MinIO) would add operational complexity without benefit at this scale.

**How it works in practice**:

1. User uploads a file through the frontend.
2. The backend receives it and writes it to the local storage root (controlled by `ARTIFACT_STORAGE_ROOT`, default `/app/storage`).
3. The backend starts a model container (Kubernetes Job) and tells it the file path via environment variables.
4. The model container reads the input from the shared volume, runs inference, and writes the result back to the same volume.
5. When the job finishes, the backend serves the result file directly — there are **no pre-signed URLs**. The frontend calls `/artifacts/{id}/preview` or `/artifacts/{id}/download` and the backend streams the file from disk.

**Where it runs**: the storage volume is declared in `docker-compose.yml` as `storage_data` and mounted into both the backend container and (when using Kubernetes) into model job pods.

### 2.5 Container Orchestration — Kubernetes

**What it is**: the mechanism by which the backend starts model containers on demand.

The backend uses the `kubernetes` Python client to create a Kubernetes **Job** — a short-lived container that runs once and exits. When a user submits a request, the backend creates a Job with the correct container image and environment variables (storage path, input file location). Kubernetes decides which node to run it on, starts the container, and the backend monitors the Job's status (pending → running → succeeded / failed).

**We use Kubernetes from day one, not just in production.** Docker Desktop includes a built-in single-node Kubernetes cluster you can enable in Settings → Kubernetes → Enable Kubernetes. Alternatively, **minikube** creates a local cluster. The exact same backend code, the same Python library calls, and the same Job manifests work on your local single-node cluster and on a multi-node production cluster. No "switching" or rewriting needed.

### 2.6 Kubernetes

**What it is**: an orchestration platform that manages containers across multiple machines (nodes). It handles:

- Starting containers on whichever node has available resources
- Restarting containers that crash
- Scaling up (more containers) when demand increases, scaling down when it decreases
- Networking between containers
- Exposing services to the outside world

**Where it runs**: in production, on a cluster (multiple machines managed by Kubernetes). For local development, you can enable Kubernetes inside Docker Desktop (Settings → Kubernetes → Enable Kubernetes), which gives you a single-node cluster on your laptop for testing. Alternatively, you can use **minikube** — a tool that creates a local Kubernetes cluster.

**What you need for Kubernetes**:

- **Enable Kubernetes in Docker Desktop**: Settings → Kubernetes → Enable Kubernetes. This gives you a single-node cluster on your machine. No extra installation.
- **kubectl**: the command-line tool for interacting with the cluster. Docker Desktop installs it automatically. If not, download: https://kubernetes.io/docs/tasks/tools/
- **minikube** (alternative if Docker Desktop's K8s doesn't work for you): https://minikube.sigs.k8s.io/docs/start/

```bash
kubectl version --client
kubectl cluster-info
```

---

## 3. Project Folder Structure

```
ai-spaces/
│
├── frontend/                        # React + Vite + Tailwind application
│   ├── public/                      # Static assets (favicon, etc.)
│   ├── src/
│   │   ├── components/              # Reusable UI components (Button, Card, ProgressBar, FileUpload, etc.)
│   │   ├── pages/                   # Full-page components
│   │   │   ├── LandingPage.tsx      # Grid of model cards — click a card to go to that model's page
│   │   │   └── ModelPage.tsx        # Single page per model: description, file input, generate button, progress indicator, result preview + download (all on one page)
│   │   ├── services/                # API client functions (talk to backend)
│   │   │   └── api.ts               # Functions like submitRequest(), getStatus(), getResult()
│   │   ├── App.tsx                  # Top-level component with routing
│   │   └── main.tsx                 # Entry point
│   ├── Dockerfile                   # Builds the frontend for production (Nginx)
│   ├── nginx.conf                   # Nginx configuration for serving the built frontend
│   ├── package.json                 # Node.js dependencies and scripts
│   ├── tsconfig.json                # TypeScript configuration
│   ├── tailwind.config.js           # Tailwind CSS configuration
│   └── vite.config.ts               # Vite build tool configuration
│
├── backend/                         # FastAPI application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app creation, startup events, middleware
│   │   ├── config.py                # Settings: database URL, storage root, auth config, etc.
│   │   ├── database.py              # SQLAlchemy engine and session setup
│   │   ├── api/                     # Route handlers (one file per resource)
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # GET /api/models — list available AI models
│   │   │   └── requests.py          # POST /api/requests, GET /api/requests/{id}, etc.
│   │   ├── db_models/               # SQLAlchemy table definitions
│   │   │   ├── __init__.py
│   │   │   ├── model.py             # Model table (name, image, input/output types)
│   │   │   └── request.py           # Request table (status, progress, file paths)
│   │   ├── schemas/                 # Pydantic models (data validation for API input/output)
│   │   │   ├── __init__.py
│   │   │   ├── model.py             # ModelResponse schema
│   │   │   └── request.py           # RequestCreate, RequestResponse schemas
│   │   └── services/                # Business logic
│   │       ├── __init__.py
│   │       ├── storage.py           # Filesystem artifact read/write operations
│   │       └── orchestrator.py      # Start/stop/monitor model containers
│   ├── tests/                       # pytest test files
│   │   ├── __init__.py
│   │   ├── test_requests.py         # Unit tests for request lifecycle
│   │   └── test_storage.py          # Unit tests for artifact storage operations
│   ├── alembic/                     # Database migration files (for schema changes)
│   │   └── versions/                # Individual migration scripts
│   ├── alembic.ini                  # Alembic configuration
│   ├── Dockerfile                   # Builds the backend for production
│   └── requirements.txt             # Python dependencies
│
├── models/                          # One subfolder per AI model
│   ├── yolo-v11/                    # Sprint 1: fully implemented, runs on CPU
│   │   ├── Dockerfile
│   │   ├── inference.py             # Reads input from shared volume, runs YOLO, writes result
│   │   └── requirements.txt         # ultralytics
│   ├── ltx-video/                   # Sprint 2: video generation via cloud GPU API
│   │   ├── Dockerfile
│   │   ├── inference.py             # Calls cloud GPU API (e.g., Replicate), writes result to shared volume
│   │   └── requirements.txt         # replicate (or huggingface_hub)
│   └── sam-3d/                      # Sprint 2: 3D object generation via cloud GPU API
│       ├── Dockerfile
│       ├── inference.py             # Calls cloud GPU API, writes GLTF result to shared volume
│       └── requirements.txt         # replicate (or huggingface_hub)
│
├── k8s/                             # Kubernetes manifests (used from day one)
│   ├── namespace.yaml               # Kubernetes namespace for the project
│   ├── model-job-template.yaml      # Template for on-demand model execution Jobs
│   ├── backend-deployment.yaml      # Backend deployment and service (for full K8s deployment)
│   ├── frontend-deployment.yaml     # Frontend deployment and service
│   ├── postgres-deployment.yaml     # PostgreSQL deployment with persistent volume
│   └── storage-pvc.yaml             # PersistentVolumeClaim for the artifact storage NFS share
│
├── docs/                            # Project documentation
│   ├── requirements.md              # Requirements specification
│   └── implementation-guide.md      # This file
│
├── docker-compose.yml               # Starts all services locally with one command
├── .env.example                     # Example environment variables (copy to .env)
├── .gitignore                       # Files and folders git should ignore
└── README.md                        # Quick start instructions
```

---

## 4. How the Services Connect (Docker Compose)

When you run `docker compose up`, Docker starts the platform services. Model containers run as Kubernetes Jobs on your local K8s cluster (Docker Desktop or minikube).

```
┌──────────────────────────────────────────────────────────────────────┐
│  Docker Compose (platform services)                                  │
│                                                                      │
│  ┌───────────┐  ┌─────────────┐  ┌───────────┐  ┌──────────────┐   │
│  │ frontend  │  │  backend    │  │ postgres  │  │  keycloak    │   │
│  │ (Nginx)   │  │  (FastAPI)  │  │           │  │  (auth/OIDC) │   │
│  │ port 3000 │─▶│  port 8000  │─▶│ port 5432 │  │  port 8080   │   │
│  └───────────┘  │             │  └───────────┘  └──────────────┘   │
│                 │             │                                      │
│                 │  ┌──────────────────────────┐                     │
│                 │  │  orchestrator            │                     │
│                 │  │  (polls backend, starts  │                     │
│                 └─▶│   model jobs)            │                     │
│                    └──────────────────────────┘                     │
│                            │                                         │
│                    ┌───────▼──────────────┐                         │
│                    │  storage_data volume │                         │
│                    │  (NFS in production) │                         │
│                    └──────────────────────┘                         │
└──────────────────────────────────────────────────────────────────────┘
                       orchestrator creates K8s Job
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Kubernetes Cluster (local: Docker Desktop / minikube)               │
│                                                                      │
│  ┌──────────────────────┐                                            │
│  │ Model Job (temporary)│  reads input from shared volume,          │
│  │ e.g. YOLO v11        │  writes result to shared volume,          │
│  │                      │  then exits                               │
│  └──────────────────────┘                                            │
└──────────────────────────────────────────────────────────────────────┘
```

**Ports you access in your browser**:

| URL | What you see |
|---|---|
| `http://localhost:3000` | The frontend (React application) |
| `http://localhost:8000/docs` | Backend API documentation (auto-generated Swagger UI) |
| `http://localhost:8080` | Keycloak admin console — manage users and realm configuration |

Inside the Docker network, containers refer to each other by service name (e.g., the backend connects to PostgreSQL at `postgres:5432` and Keycloak at `keycloak:8080`). These internal addresses are configured in the `docker-compose.yml` file.

---

## 5. How a User Request Flows Through the System

This is the complete sequence of what happens when a user uploads an image for YOLO v11 detection:

```
Step 1: User opens http://localhost:3000
        → Frontend serves the landing page with space cards

Step 2: User clicks on a space card (e.g. "YOLO v11")
        → Frontend navigates to the space's job submission page

Step 3: User selects an image file and clicks "Submit"
        → Frontend sends the file to POST /jobs as multipart/form-data

Step 4: Backend receives the file
        → Writes the image to the shared storage volume:
            {ARTIFACT_STORAGE_ROOT}/{job_id}/inputs/image.jpg
        → Creates a row in the jobs table: status=QUEUED
        → Returns the job_id to the frontend

Step 5: The orchestrator picks up the queued job
        → Calls GET /internal/jobs (pending jobs list)
        → Creates a Kubernetes Job using the job template with:
            Container image: ai-spaces-yolo-v11
            Environment variables:
              ARTIFACT_STORAGE_ROOT=/app/storage
              INPUT_PATH={job_id}/inputs/image.jpg
              OUTPUT_DIR={job_id}/outputs/
              JOB_ID={job_id}
              BACKEND_URL=http://backend:8000
              INTERNAL_SERVICE_TOKEN=...

Step 6: The job detail page shows progress
        → Every 2 seconds, calls GET /jobs/{job_id}
        → Backend returns current status, progress_percent, progress_message

Step 7: Inside the YOLO v11 K8s Job
        → Reads image from shared volume (inputs/{job_id}/image.jpg)
        → Reports progress via PATCH /internal/jobs/{id}/progress
        → Runs YOLO v11 detection
        → Writes annotated image to shared volume (outputs/{job_id}/result.jpg)
        → Reports completion via PATCH /internal/jobs/{id}/succeed
        → Container exits with code 0

Step 8: Backend detects the job succeeded (via the internal PATCH)
        → Updates the database row: status=SUCCEEDED
        → Creates an artifact row pointing to the output file

Step 9: The job detail page sees status=SUCCEEDED
        → Calls GET /jobs/{job_id}/artifacts
        → Displays each artifact using ArtifactViewer
        → Preview: GET /artifacts/{artifact_id}/preview  (backend streams the file)
        → Download: GET /artifacts/{artifact_id}/download
        → No pre-signed URLs — the backend serves the file directly from disk
```

---

## 6. Environment Variables

The project uses a `.env` file (not committed to git) to store configuration. Each team member copies `.env.example` to `.env` on their machine.

```bash
# PostgreSQL
POSTGRES_USER=aispacesuser
POSTGRES_PASSWORD=aispacespass
POSTGRES_DB=aispaces
DATABASE_URL=postgresql+asyncpg://aispacesuser:aispacespass@postgres:5432/aispaces

# Keycloak (identity provider)
# Admin UI at http://localhost:8080 — username: admin, password: admin (dev only)

# Backend
BACKEND_PORT=8000

# Artifact storage — path inside the backend container (mounted from Docker volume)
ARTIFACT_STORAGE_ROOT=/app/storage

# Internal service token — shared secret between backend and orchestrator
INTERNAL_SERVICE_TOKEN=changeme-internal-token

# Auth (OIDC / Keycloak)
AUTH_PROVIDER=oidc
OIDC_ISSUER=http://localhost:8080/realms/ai-spaces
OIDC_JWKS_URL=http://keycloak:8080/realms/ai-spaces/protocol/openid-connect/certs
OIDC_CLIENT_ID=ai-spaces-frontend
OIDC_VERIFY_AUDIENCE=false
```

---

## 7. Key Commands Reference

### Starting the entire platform

```bash
docker compose up --build
```

This builds all Docker images (frontend, backend, orchestrator) and starts all containers (frontend, backend, PostgreSQL, Keycloak, orchestrator). The `--build` flag ensures images are rebuilt if code changed. First run will take several minutes to download base images. Subsequent runs are fast.

### Stopping the platform

```bash
docker compose down
```

Add `-v` to also delete stored data (database contents, artifact files, Keycloak data):

```bash
docker compose down -v
```

### Running the backend locally (outside Docker, for faster development)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The `--reload` flag means the server restarts automatically when you save a file. You still need PostgreSQL and Keycloak running (via Docker Compose or standalone containers).

### Running the frontend locally (outside Docker, for faster development)

```bash
cd frontend
npm install
npm run dev
```

This starts the Vite dev server with hot reload at `http://localhost:5173`.

### Running backend tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

### Building model containers

```bash
docker build -t ai-spaces-yolo-v11 ./models/yolo-v11
docker build -t ai-spaces-ltx-video ./models/ltx-video
docker build -t ai-spaces-sam-3d ./models/sam-3d
```

### Loading model images into your local Kubernetes cluster

If using minikube, Docker images on your machine are not automatically visible to the cluster. Load them:

```bash
minikube image load ai-spaces-yolo-v11
```

If using Docker Desktop's built-in Kubernetes, images are shared automatically.

### Checking Kubernetes Jobs

```bash
kubectl get jobs -n ai-spaces
kubectl get pods -n ai-spaces
kubectl logs job/yolo-v11-abc123 -n ai-spaces
```

### Viewing logs from a specific service

```bash
docker compose logs backend --follow
docker compose logs orchestrator --follow
```

### Accessing the PostgreSQL database directly (for debugging)

```bash
docker compose exec postgres psql -U aispaces -d aispaces
```

This opens an interactive SQL prompt inside the running PostgreSQL container. Type `\dt` to list tables, `SELECT * FROM requests;` to see all requests, `\q` to quit.

---

## 8. Database Schema

These tables are created by SQLAlchemy when the backend starts (or via Alembic migrations).

### `models` table

| Column | Type | Description |
|---|---|---|
| id | text (primary key) | Unique identifier, e.g., `yolo-v11` |
| name | text | Display name, e.g., "YOLO v11 Object Detection" |
| description | text | Short description shown on the model card |
| docker_image | text | Docker image name, e.g., `ai-spaces-yolo-v11` |
| input_type | text | Expected input, e.g., "image/jpeg, image/png" |
| output_type | text | What it produces, e.g., "image/jpeg" |
| max_file_size_mb | integer | Maximum allowed input file size |

### `requests` table

| Column | Type | Description |
|---|---|---|
| id | text (primary key) | UUID generated when the request is created |
| model_id | text (foreign key → models.id) | Which model was selected |
| status | text | One of: `starting`, `processing`, `completed`, `failed` |
| progress | integer | 0–100 percentage |
| progress_step | text | Human-readable step, e.g., "Running detection" |
| input_key | text | Storage path to the uploaded input file |
| output_key | text | Storage path to the result file (null until completed) |
| error_message | text | Error description if status is `failed` (null otherwise) |
| container_id | text | Docker container ID (for monitoring) |
| created_at | timestamp | When the request was submitted |
| updated_at | timestamp | When the status last changed |

---

## 9. Model Container Contract

Every AI model in the platform is packaged as a Docker container that follows the same interface. This is what makes adding new models possible without changing the backend or frontend.

### What the container receives (environment variables)

| Variable | Example value | Purpose |
|---|---|---|
| `JOB_ID` | `a1b2c3d4` | Unique identifier for this job |
| `ARTIFACT_STORAGE_ROOT` | `/app/storage` | Root of the shared storage volume |
| `INPUT_PATH` | `a1b2c3d4/inputs/image.jpg` | Relative path to the input file within the storage root |
| `OUTPUT_DIR` | `a1b2c3d4/outputs/` | Relative directory to write output files into |
| `BACKEND_URL` | `http://backend:8000` | Backend API base URL (for progress reporting) |
| `INTERNAL_SERVICE_TOKEN` | `...` | Shared secret for internal API calls |

### What the container must do

1. Read the input file from `{ARTIFACT_STORAGE_ROOT}/{INPUT_PATH}`.
2. Run the model inference.
3. Write result file(s) to `{ARTIFACT_STORAGE_ROOT}/{OUTPUT_DIR}`.
4. Periodically report progress via `PATCH {BACKEND_URL}/internal/jobs/{JOB_ID}/progress`:
   ```json
   {"progress_percent": 42, "progress_message": "Running detection"}
   ```
5. Report completion via `PATCH {BACKEND_URL}/internal/jobs/{JOB_ID}/succeed`.
6. Exit with code 0 on success, non-zero on failure.

### Adding a new model

To add a new model to the platform:

1. Create a new folder under `models/` (e.g., `models/ltx-video/`).
2. Write a `Dockerfile` and `inference.py` that follows the contract above.
3. Build the Docker image: `docker build -t ai-spaces-ltx-video ./models/ltx-video`.
4. Add a row to the `models` database table (via a seed script or migration) with the image name and I/O types.
5. The model automatically appears on the landing page. No backend or frontend code changes needed.

---

## 10. Development Workflow

### Day-to-day development

For faster iteration, you run the frontend and backend directly on your machine (not in Docker), while PostgreSQL and Keycloak run in Docker:

```bash
docker compose up postgres keycloak
```

Then in separate terminals:

```bash
# Terminal 1: backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: frontend
cd frontend
npm run dev
```

This way, changes to your Python or TypeScript code are reflected instantly without rebuilding Docker images.

### Before committing

Run the full Docker Compose setup to verify everything works end-to-end:

```bash
docker compose up --build
```

### Git branching

Use a simple branching model:

- `main` — stable, working code only. Protected: no direct pushes.
- `feature/xyz` — one branch per feature or user story. Create a pull request to merge into main.
- Every pull request must be reviewed by at least one team member before merging.

```bash
git checkout -b feature/us01-model-cards
# ... make changes ...
git add .
git commit -m "Add model cards to landing page"
git push -u origin feature/us01-model-cards
# ... create pull request on GitHub ...
```
