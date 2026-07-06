# AI-Spaces – Quick Start

There are two ways to run the application locally.

Docker Compose is the simpler option and takes about 5 minutes. Kubernetes with kind is more involved but shows the full stack with Keycloak login and both AI Spaces running.

---

## Option A: Docker Compose

Everything runs in Docker, no need to start services manually.

Requirements: Docker Desktop, Python 3.12+, Node 20+

### Steps

1. Clone the repository and create the .env file

```bash
git clone https://gitlab.hof-university.de/atilla888/ai-spaces.git
cd ai-spaces
cp .env.example .env
```

2. Install Python dependencies

Mac / Linux:
```bash
python3 -m venv venv
venv/bin/pip install -r apps/backend/requirements.txt
venv/bin/pip install -r apps/orchestrator/requirements.txt
```

Windows (PowerShell):
```powershell
python -m venv venv
venv\Scripts\pip install -r apps\backend\requirements.txt
venv\Scripts\pip install -r apps\orchestrator\requirements.txt
```

3. Install frontend dependencies

```bash
cd apps/frontend
npm install
cd ../..
```

4. Start all services

```bash
docker compose up
```

This starts Postgres, Keycloak, the backend and the orchestrator together. After about 30 seconds Keycloak is ready. Then open a second terminal for the frontend:

```bash
cd apps/frontend
npm run dev
```

5. Open the app at http://localhost:5173

The backend runs with `AUTH_PROVIDER=oidc`. To log in, a user needs to be created in Keycloak once (see next step).

6. Create a Keycloak test user

Run this once while `docker compose up` is running:

```bash
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8080/realms/master/protocol/openid-connect/token \
  -d "client_id=admin-cli&grant_type=password&username=admin&password=admin" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST http://localhost:8080/admin/realms/ai-spaces/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","firstName":"Test","lastName":"User","enabled":true,"credentials":[{"type":"password","value":"test123","temporary":false}]}'

USER_ID=$(curl -s "http://localhost:8080/admin/realms/ai-spaces/users?username=testuser" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")
ROLE=$(curl -s http://localhost:8080/admin/realms/ai-spaces/roles/admin \
  -H "Authorization: Bearer $ADMIN_TOKEN")
curl -s -X POST "http://localhost:8080/admin/realms/ai-spaces/users/$USER_ID/role-mappings/realm" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" -d "[$ROLE]"

echo "Done – login with testuser / test123"
```

7. Run database migrations

```bash
# Mac / Linux
cd apps/backend
../../venv/bin/alembic upgrade head

# Windows
cd apps\backend
..\..\venv\Scripts\alembic upgrade head
```

Quick check:
```bash
curl http://localhost:8000/health
# expected: {"status":"ok"}
```

To stop:
```bash
docker compose down
# in the frontend terminal: Ctrl+C
```

---

## Option B: Kubernetes with kind

Full stack on a local Kubernetes cluster. Includes Keycloak, both AI Spaces in mock mode and the real orchestrator.

Requirements: Docker Desktop, Python 3.12+, Node 20+, kubectl (`brew install kubectl`)

`kind` is installed automatically by the setup script via Homebrew on Mac or a binary download on Linux.

### Automated setup

```bash
bash scripts/setup-kind.sh
```

The script does the following (takes about 5–10 minutes):
1. Install kind if not already present
2. Create a cluster named `ai-spaces`
3. Build all Docker images
4. Load images into the cluster
5. Deploy all services (Postgres, Keycloak, backend, orchestrator, frontend)
6. Wait for all pods to be ready
7. Start port-forwards
8. Create a Keycloak test user
9. Register both mock Spaces (ACE-Step and SAM 3D)

When finished you will see:

```
Frontend:  http://localhost:5173   (login: testuser / test123)
Backend:   http://localhost:8000
Keycloak:  http://localhost:8080   (admin: admin / admin123)
```

### Restore port-forwards after a restart

Port-forwards do not survive closing the terminal. To restore them:

```bash
kubectl port-forward -n ai-spaces svc/frontend 5173:80 &
kubectl port-forward -n ai-spaces svc/backend 8000:8000 &
kubectl port-forward -n ai-spaces svc/keycloak 8080:8080 &
```

### Delete the cluster

```bash
kind delete cluster --name ai-spaces
```

---

## Common problems

| Problem | Solution |
|---|---|
| `docker: command not found` | Docker Desktop is not running |
| Backend cannot reach Postgres | Change `localhost` to `127.0.0.1` in `DATABASE_URL` in `.env` |
| Login redirect loop | Keycloak is not ready yet – wait 30 seconds and try again |
| Job is submitted but nothing happens | Orchestrator is not running (Option A: it is included in `docker compose up`) |
| Port already in use | `lsof -i :8000` (Mac/Linux) or `netstat -ano \| findstr :8000` (Windows) |
| kind cluster already exists | `kind delete cluster --name ai-spaces` then run the script again |

### Dev mode (skip login)

Set `AUTH_PROVIDER=dev` in `.env` and restart the backend. In dev mode every request is treated as admin, Keycloak is not needed.
