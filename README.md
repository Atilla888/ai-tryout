# AI Spaces

A university platform for running AI models (object detection, video generation, 3D reconstruction) through a web interface. Users upload files, the platform runs inference in isolated Kubernetes Jobs, and results are returned for preview and download.

## Prerequisites

- [Git](https://git-scm.com/downloads)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- [Node.js v20+](https://nodejs.org/) (LTS)
- [Python 3.11+](https://www.python.org/downloads/)

## Quick Start

1. **Clone the repository and create your `.env` file:**

   ```bash
   git clone <repo-url> ai-spaces
   cd ai-spaces
   cp .env.example .env
   ```

2. **Start all services:**

   ```bash
   docker compose up --build
   ```

3. **Open in your browser:**

   | URL | Service |
   |---|---|
   | http://localhost:3000 | Frontend |
   | http://localhost:8000/docs | Backend API (Swagger UI) |
   | http://localhost:5050 | pgAdmin (database browser) |
   | http://localhost:9001 | MinIO console (file storage) |

## Development Workflow

For faster iteration, run infrastructure in Docker and the app locally:

```bash
# Start only infrastructure services
docker compose up postgres minio pgadmin

# Terminal 1: backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2: frontend
cd frontend
npm install
npm run dev
```

## Running Tests

```bash
cd backend
pytest tests/ -v
```

## Project Structure

```
ai-spaces/
├── frontend/          # React + Vite + Tailwind (TypeScript)
├── backend/           # FastAPI + SQLAlchemy (Python)
├── models/            # AI model containers (one per model)
│   ├── yolo-v11/      # Object detection (Sprint 1)
│   ├── ltx-video/     # Video generation (Sprint 2)
│   └── sam-3d/        # 3D reconstruction (Sprint 2)
├── k8s/               # Kubernetes manifests
├── docs/              # Project documentation
├── docker-compose.yml # Local multi-service setup
└── .env.example       # Environment variable template
```

See [docs/implementation-guide.md](docs/implementation-guide.md) for detailed explanations of every technology and how the services connect.
