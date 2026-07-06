#!/usr/bin/env bash
# Automated kind cluster setup for AI-Spaces
# Usage: bash scripts/setup-kind.sh
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

step() { echo -e "${BLUE}==> $*${NC}"; }
ok()   { echo -e "${GREEN}[ok] $*${NC}"; }
warn() { echo -e "${YELLOW}[!]  $*${NC}"; }
die()  { echo -e "${RED}[error] $*${NC}"; exit 1; }

CLUSTER_NAME=ai-spaces
NAMESPACE=ai-spaces
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── 1. Prerequisites ──────────────────────────────────────────────────────────
step "Checking prerequisites"
command -v docker   &>/dev/null || die "Docker is not installed"
docker info         &>/dev/null || die "Docker daemon is not running — start Docker Desktop first"
command -v kubectl  &>/dev/null || die "kubectl is not installed (brew install kubectl)"

if ! command -v kind &>/dev/null; then
  step "Installing kind"
  if command -v brew &>/dev/null; then
    brew install kind
  else
    curl -Lo /usr/local/bin/kind \
      "https://kind.sigs.k8s.io/dl/v0.26.0/kind-$(uname -s | tr '[:upper:]' '[:lower:]')-amd64"
    chmod +x /usr/local/bin/kind
  fi
fi
ok "kind $(kind version)"

# ── 2. Create cluster ─────────────────────────────────────────────────────────
step "Creating kind cluster '$CLUSTER_NAME'"
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
  warn "Cluster '$CLUSTER_NAME' already exists — skipping creation"
else
  kind create cluster --name "$CLUSTER_NAME" \
    --config "$ROOT_DIR/infra/kind/kind-config.yml"
fi
kubectl config use-context "kind-${CLUSTER_NAME}"
ok "Cluster ready"

# ── 3. Build Docker images ────────────────────────────────────────────────────
step "Building Docker images (this takes a few minutes)"
docker build -q -t ai-spaces-backend:dev      "$ROOT_DIR/apps/backend"       && ok "  backend"
docker build -q -t ai-spaces-frontend:dev     "$ROOT_DIR/apps/frontend"      && ok "  frontend"
docker build -q -t ai-spaces-orchestrator:dev "$ROOT_DIR/apps/orchestrator"  && ok "  orchestrator"
docker build -q -t ai-spaces-acestep-mock:dev \
  -f "$ROOT_DIR/apps/acestep-runner/Dockerfile.mock" "$ROOT_DIR/apps/acestep-runner" && ok "  acestep-mock"
docker build -q -t ai-spaces-sam3d-mock:dev \
  -f "$ROOT_DIR/apps/sam3d-runner/Dockerfile.mock" "$ROOT_DIR/apps/sam3d-runner"     && ok "  sam3d-mock"

# ── 4. Load images into kind ──────────────────────────────────────────────────
step "Loading images into kind cluster"
kind load docker-image ai-spaces-backend:dev      --name "$CLUSTER_NAME"
kind load docker-image ai-spaces-frontend:dev     --name "$CLUSTER_NAME"
kind load docker-image ai-spaces-orchestrator:dev --name "$CLUSTER_NAME"
kind load docker-image ai-spaces-acestep-mock:dev --name "$CLUSTER_NAME"
kind load docker-image ai-spaces-sam3d-mock:dev   --name "$CLUSTER_NAME"
ok "All images loaded"

# ── 5. Namespace ──────────────────────────────────────────────────────────────
step "Creating namespace"
kubectl apply -f "$ROOT_DIR/infra/k8s/namespace.yml"

# ── 6. Secrets ────────────────────────────────────────────────────────────────
step "Creating secrets"
DB_PASS="aispacespass"
INTERNAL_TOKEN="changeme-internal-token"

kubectl -n "$NAMESPACE" create secret generic postgres-secret \
  --from-literal=POSTGRES_USER=aispacesuser \
  --from-literal=POSTGRES_PASSWORD="$DB_PASS" \
  --from-literal=POSTGRES_DB=aispaces \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "$NAMESPACE" create secret generic keycloak-secret \
  --from-literal=KC_BOOTSTRAP_ADMIN_USERNAME=admin \
  --from-literal=KC_BOOTSTRAP_ADMIN_PASSWORD=admin123 \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "$NAMESPACE" create secret generic backend-secret \
  --from-literal=DATABASE_URL="postgresql+asyncpg://aispacesuser:${DB_PASS}@postgres:5432/aispaces" \
  --from-literal=ALEMBIC_DATABASE_URL="postgresql+psycopg://aispacesuser:${DB_PASS}@postgres:5432/aispaces" \
  --from-literal=INTERNAL_SERVICE_TOKEN="$INTERNAL_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

ok "Secrets applied"

# ── 7. Storage ────────────────────────────────────────────────────────────────
# kind doesn't support NFS PersistentVolumes; use hostPath instead.
step "Creating hostPath storage"
kubectl apply -f - <<STORAGE_EOF
apiVersion: v1
kind: PersistentVolume
metadata:
  name: ai-spaces-artifacts-pv
spec:
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ""
  hostPath:
    path: /tmp/ai-spaces-artifacts
    type: DirectoryOrCreate
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ai-spaces-artifacts-pvc
  namespace: ${NAMESPACE}
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: ""
  volumeName: ai-spaces-artifacts-pv
  resources:
    requests:
      storage: 5Gi
STORAGE_EOF
ok "Storage ready"

# ── 8. Deploy services ────────────────────────────────────────────────────────
step "Deploying Postgres"
kubectl apply -f "$ROOT_DIR/infra/k8s/postgres.yml"
kubectl -n "$NAMESPACE" rollout status statefulset/postgres --timeout=120s

step "Deploying Keycloak (includes realm import)"
kubectl apply -k "$ROOT_DIR/infra/k8s/keycloak/"
kubectl -n "$NAMESPACE" rollout status deployment/keycloak --timeout=240s

step "Deploying backend"
kubectl apply -f "$ROOT_DIR/infra/k8s/backend.yml"
kubectl -n "$NAMESPACE" rollout status deployment/backend --timeout=180s

step "Deploying orchestrator"
kubectl apply -f "$ROOT_DIR/infra/k8s/orchestrator.yml"
kubectl -n "$NAMESPACE" rollout status deployment/orchestrator --timeout=120s

step "Deploying frontend"
kubectl apply -f "$ROOT_DIR/infra/k8s/frontend.yml"
kubectl -n "$NAMESPACE" rollout status deployment/frontend --timeout=60s

ok "All pods running"

# ── 9. Port-forwards ──────────────────────────────────────────────────────────
step "Starting port-forwards in background"
pkill -f "kubectl port-forward.*${NAMESPACE}" 2>/dev/null || true
sleep 1
kubectl port-forward -n "$NAMESPACE" svc/backend  8000:8000 &>/tmp/pf-backend.log  &
kubectl port-forward -n "$NAMESPACE" svc/keycloak 8080:8080 &>/tmp/pf-keycloak.log &
kubectl port-forward -n "$NAMESPACE" svc/frontend 5173:80   &>/tmp/pf-frontend.log  &
sleep 3
ok "Port-forwards running (logs in /tmp/pf-*.log)"

# ── 10. Keycloak test user ────────────────────────────────────────────────────
step "Creating Keycloak user testuser / test123"
ADMIN_TOKEN=""
for i in $(seq 1 24); do
  ADMIN_TOKEN=$(curl -sf -X POST http://localhost:8080/realms/master/protocol/openid-connect/token \
    -d "client_id=admin-cli&grant_type=password&username=admin&password=admin123" \
    2>/dev/null \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || true)
  [ -n "$ADMIN_TOKEN" ] && break
  echo "  Waiting for Keycloak... ($i/24)"
  sleep 5
done
[ -n "$ADMIN_TOKEN" ] || die "Keycloak did not become ready — check: kubectl -n $NAMESPACE logs deploy/keycloak"

curl -sf -X POST http://localhost:8080/admin/realms/ai-spaces/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username":"testuser","email":"test@example.com",
    "firstName":"Test","lastName":"User","enabled":true,
    "credentials":[{"type":"password","value":"test123","temporary":false}]
  }' 2>/dev/null || warn "User may already exist — continuing"

USER_ID=$(curl -sf "http://localhost:8080/admin/realms/ai-spaces/users?username=testuser" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")

ROLE=$(curl -sf "http://localhost:8080/admin/realms/ai-spaces/roles/admin" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

curl -sf -X POST \
  "http://localhost:8080/admin/realms/ai-spaces/users/$USER_ID/role-mappings/realm" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "[$ROLE]" 2>/dev/null || warn "Role mapping may already exist — continuing"

ok "Keycloak user ready"

# ── 11. Register mock AI Spaces ───────────────────────────────────────────────
step "Registering mock AI Spaces via backend API"

USER_TOKEN=$(curl -sf -X POST \
  "http://localhost:8080/realms/ai-spaces/protocol/openid-connect/token" \
  -d "client_id=ai-spaces-frontend&grant_type=password&username=testuser&password=test123" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

# ACE-Step mock
curl -sf -X POST "http://localhost:8000/spaces" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "acestep-music",
    "name": "ACE-Step 1.5 — Text to Music",
    "description": "Generate a music track from a style prompt. Mock mode returns a sine-wave WAV.",
    "task_type": "Audio",
    "input_types": ["text"],
    "output_types": ["audio"],
    "container_image": "ai-spaces-acestep-mock:dev",
    "visibility": "PUBLIC",
    "status": "PUBLISHED",
    "ui_config": {
      "inputs": [
        {
          "name": "prompt",
          "type": "text",
          "label": "Style / prompt",
          "required": true,
          "maxLength": 512
        },
        {
          "name": "lyrics",
          "type": "text",
          "label": "Lyrics (optional)",
          "required": false,
          "maxLength": 4096
        }
      ]
    }
  }' 2>/dev/null && ok "  ACE-Step registered" || warn "  ACE-Step: already registered or API error (safe to ignore)"

# SAM 3D mock
curl -sf -X POST "http://localhost:8000/spaces" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "sam-3d-objects",
    "name": "3D Generator – SAM 3D Objects",
    "description": "Upload a photo and get a 3D model (.glb). Mock mode returns a blue cube.",
    "task_type": "image-to-3d",
    "input_types": ["image"],
    "output_types": ["3d"],
    "container_image": "ai-spaces-sam3d-mock:dev",
    "visibility": "PUBLIC",
    "status": "PUBLISHED",
    "ui_config": {
      "inputs": [
        {
          "name": "image",
          "type": "image_upload",
          "label": "Input Image",
          "required": true,
          "mime_types": ["image/png","image/jpeg","image/webp"],
          "max_size_mb": 20
        }
      ],
      "outputs": [
        {
          "name": "model",
          "type": "3d",
          "label": "3D Model (.glb)"
        }
      ]
    }
  }' 2>/dev/null && ok "  SAM 3D registered" || warn "  SAM 3D: already registered or API error (safe to ignore)"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo ""
echo -e "  Frontend:  ${BLUE}http://localhost:5173${NC}   login: testuser / test123"
echo -e "  Backend:   ${BLUE}http://localhost:8000${NC}"
echo -e "  Keycloak:  ${BLUE}http://localhost:8080${NC}   admin: admin / admin123"
echo ""
echo -e "  Restart port-forwards after reboot:"
echo -e "    kubectl port-forward -n $NAMESPACE svc/frontend 5173:80 &"
echo -e "    kubectl port-forward -n $NAMESPACE svc/backend  8000:8000 &"
echo -e "    kubectl port-forward -n $NAMESPACE svc/keycloak 8080:8080 &"
echo ""
echo -e "  Delete cluster:  kind delete cluster --name $CLUSTER_NAME"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
