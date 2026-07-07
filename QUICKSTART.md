# AI-Spaces Quick Start

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

The backend runs with `AUTH_PROVIDER=oidc`, and the realm import already ships ready-to-use accounts, so no user setup is needed.

6. Log in

Log in with username `admin` and password `admin123`. This account has the `admin` and `space_creator` roles. Two more accounts are seeded for testing: `creator` / `creator123` (can create Spaces) and `user` / `user123` (a normal end user). You can also register a brand new account from the login page.

Prefer no login at all? Set `AUTH_PROVIDER=dev` in `.env` and restart the backend, and every request is then treated as admin without needing Keycloak.

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

Full stack on a local Kubernetes cluster: Postgres, Keycloak login, NFS artifact storage, the real orchestrator, and both AI Spaces (ACE-Step music and SAM 3D) running in CPU mock mode, so no GPU is needed.

Requirements: Docker Desktop, `kubectl`, and `kind`.
- **Mac/Linux:** the setup script installs `kind` for you (Homebrew or binary download). It also uses `python3` (already on macOS) to read tokens.
- **Windows:** install `kind` and `kubectl` yourself first, e.g. `winget install Kubernetes.kind Kubernetes.kubectl`.

The scripts live in `scripts/mac-linux/` and `scripts/windows/`, with the same three per OS: **`up`** (bring the stack up), **`seed`** (register the two Spaces), **`down`** (tear down). `up` does:

1. Create a kind cluster named `ai-spaces`
2. Start an NFS server for artifact storage on the cluster's docker network
3. Build the five images and load them into the cluster
4. Apply secrets and deploy Postgres, Keycloak (with realm import), backend, orchestrator, frontend
5. Wait for all pods to be ready

The whole thing takes about 5 to 10 minutes.

### Mac / Linux

```bash
bash scripts/mac-linux/up.sh     # deploy everything + start port-forwards
bash scripts/mac-linux/seed.sh   # register the two Spaces
```

### Windows (PowerShell)

```powershell
./scripts/windows/up.ps1

# up.ps1 prints these two commands. Run each in its own terminal and leave them open:
kubectl port-forward svc/keycloak 8080:8080 -n ai-spaces
kubectl port-forward svc/frontend 5173:80   -n ai-spaces

./scripts/windows/seed.ps1       # register the two Spaces
```

Then open http://localhost:5173 and log in as **admin / admin123**.

> One platform difference: on Mac/Linux `up.sh` starts the port-forwards for you; on Windows `up.ps1` prints the two commands to run (Windows background forwards are less reliable). `seed` also spins up a temporary forward if it can't reach them.

> **Windows/WSL note:** `up.ps1` pins `kindest/node:v1.34.0` because kind's default (v1.35.0) fails to boot on newer WSL2 kernels ("could not find a log line ... Reached target Multi-User System"). If cluster creation fails, run `wsl --shutdown`, restart Docker Desktop, and re-run.

### Using the app

- **Run a job:** open **SAM 3D**, upload a photo, and submit to get back a `.glb`. Or open **ACE-Step**, enter a prompt, and get back a `.wav`. Each job runs as a Kubernetes Job, which you can watch with `kubectl get jobs -n ai-spaces -w`.
- **Create your own Space:** go to the Creator dashboard, open My Spaces, and click New Space. Set the container image to a loaded runner (`ai-spaces-sam3d:latest` or `ai-spaces-acestep:latest`), define the input form, then Validate and Publish.

### Restore port-forwards after a restart

Port-forwards do not survive closing the terminal. Only these two are needed (nginx in the frontend pod proxies `/api` to the backend):

```bash
kubectl port-forward -n ai-spaces svc/frontend 5173:80 &
kubectl port-forward -n ai-spaces svc/keycloak 8080:8080 &
```

### Tear down

```bash
# Mac/Linux  (add --wipe to also delete stored artifacts)
bash scripts/mac-linux/down.sh

# Windows    (add -Wipe to also delete stored artifacts)
./scripts/windows/down.ps1
```

---

## Common problems

| Problem | Solution |
|---|---|
| `docker: command not found` | Docker Desktop is not running |
| Backend cannot reach Postgres | Change `localhost` to `127.0.0.1` in `DATABASE_URL` in `.env` |
| Login redirect loop | Keycloak is not ready yet, wait 30 seconds and try again |
| Job is submitted but nothing happens | Orchestrator is not running (Option A: it is included in `docker compose up`) |
| Port already in use | `lsof -i :8000` (Mac/Linux) or `netstat -ano \| findstr :8000` (Windows) |
| kind cluster already exists | `kind delete cluster --name ai-spaces` then run the script again |
| kind: "could not find a log line ... Reached target Multi-User System" | Node image too new for your kernel. Scripts pin `v1.34.0`; if it still fails, `wsl --shutdown` (Windows) and restart Docker Desktop, then retry |
| Runner job stuck in `ImagePullBackOff` | Its image wasn't loaded into kind, rebuild it and `kind load docker-image <tag> --name ai-spaces` |

### Dev mode (skip login)

Set `AUTH_PROVIDER=dev` in `.env` and restart the backend. In dev mode every request is treated as admin, Keycloak is not needed.
