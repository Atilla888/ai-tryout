# AI-Spaces — Quick Start

Two paths to a running application. Pick the one that fits your setup.

| | Path A: Docker Compose | Path B: Kubernetes (kind) |
|---|---|---|
| Setup time | ~5 minutes | ~10 minutes |
| Requirements | Docker, Python 3.12+, Node 20+ | Docker, Python 3.12+, Node 20+ |
| Runs on | Mac, Windows, Linux | Mac, Linux (Windows: WSL2) |
| Auth | Dev mode (no login needed) | Keycloak (full OIDC login) |
| AI Spaces | Fake runner (text only) | ACE-Step + SAM 3D (mock) |
| Good for | Quick look, testing the API | Full platform demo |

---

## Path A: Docker Compose

Everything runs in Docker. No manual service management.

### Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Python 3.12+ with `pip`
- Node 20+

### Steps

**1. Clone and configure**

```bash
git clone https://gitlab.hof-university.de/atilla888/ai-spaces.git
cd ai-spaces
cp .env.example .env
```

**2. Create Python venv and install dependencies**

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

**3. Install frontend dependencies**

```bash
cd apps/frontend
npm install
cd ../..
```

**4. Start everything**

```bash
docker compose up
```

This starts Postgres, Keycloak, the backend, and the orchestrator together.
Wait ~30 seconds for Keycloak to be ready, then open a second terminal for the frontend:

```bash
cd apps/frontend
npm run dev
```

**5. Open the app**

http://localhost:5173

The backend runs with `AUTH_PROVIDER=oidc` in Docker Compose. To log in,
create a Keycloak user (see step 6) or switch to dev mode (see Troubleshooting).

**6. Create a login user (Keycloak)**

Run this once after `docker compose up`:

```bash
# Get admin token
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8080/realms/master/protocol/openid-connect/token \
  -d "client_id=admin-cli&grant_type=password&username=admin&password=admin" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

# Create user
curl -s -X POST http://localhost:8080/admin/realms/ai-spaces/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","firstName":"Test","lastName":"User","enabled":true,"credentials":[{"type":"password","value":"test123","temporary":false}]}'

# Assign admin role
USER_ID=$(curl -s "http://localhost:8080/admin/realms/ai-spaces/users?username=testuser" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")
ROLE=$(curl -s http://localhost:8080/admin/realms/ai-spaces/roles/admin \
  -H "Authorization: Bearer $ADMIN_TOKEN")
curl -s -X POST "http://localhost:8080/admin/realms/ai-spaces/users/$USER_ID/role-mappings/realm" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" -d "[$ROLE]"

echo "Done — login with testuser / test123"
```

**7. Apply database migrations**

```bash
# Mac / Linux
cd apps/backend
../../venv/bin/alembic upgrade head

# Windows
cd apps\backend
..\..\venv\Scripts\alembic upgrade head
```

### Check it works

```bash
curl http://localhost:8000/health
# expected: {"status":"ok"}
```

### Stop

```bash
docker compose down
# also in the frontend terminal: Ctrl+C
```

---

## Path B: Kubernetes with kind

Full platform on a local Kubernetes cluster. Includes Keycloak, both mock AI Spaces, and the full orchestrator.

### Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Python 3.12+ with `pip`
- Node 20+
- `kubectl` installed (`brew install kubectl` on Mac)

The setup script installs `kind` automatically via Homebrew (Mac) or the kind release binary (Linux).

### One-command setup

```bash
bash scripts/setup-kind.sh
```

The script (~5 minutes):
1. Installs `kind` if missing
2. Creates a cluster named `ai-spaces`
3. Builds all three Docker images (backend, frontend, orchestrator)
4. Loads images into the cluster
5. Deploys all services (Postgres, Keycloak, backend, orchestrator, frontend)
6. Waits for all pods to be ready
7. Starts port-forwards
8. Creates a test user in Keycloak
9. Registers both mock AI Spaces (ACE-Step + SAM 3D)

When it finishes you will see:

```
Frontend:  http://localhost:5173   (login: testuser / test123)
Backend:   http://localhost:8000
Keycloak:  http://localhost:8080   (admin: admin / admin123)
```

### Manual steps (if the script fails)

See the commands inside `scripts/setup-kind.sh` — every step is documented inline.

### Restart port-forwards after reboot

Port-forwards do not survive a terminal close. Run this to restore them:

```bash
kubectl port-forward -n ai-spaces svc/frontend 5173:80 &
kubectl port-forward -n ai-spaces svc/backend 8000:8000 &
kubectl port-forward -n ai-spaces svc/keycloak 8080:8080 &
```

### Stop / delete cluster

```bash
kind delete cluster --name ai-spaces
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `docker: command not found` | Docker Desktop is not running |
| Backend can't reach Postgres | In `.env` change `localhost` to `127.0.0.1` in `DATABASE_URL` |
| Login redirect loop | Keycloak not started yet — wait 30s and retry |
| Job submitted, nothing happens | Orchestrator not running — start it (Path A: it's in `docker compose up`) |
| Port already in use | `lsof -i :8000` (Mac/Linux) or `netstat -ano | findstr :8000` (Windows) |
| Kind cluster already exists | `kind delete cluster --name ai-spaces` then run script again |

### Dev mode (skip login entirely)

Edit `.env` and set `AUTH_PROVIDER=dev`, then restart the backend.
In dev mode every request is treated as admin — no Keycloak needed.
