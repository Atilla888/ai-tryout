#!/usr/bin/env bash
# Bring up the whole AI-Spaces stack on a local kind cluster (Mac/Linux).
# Windows users: run scripts/windows/up.ps1 instead (same workflow in PowerShell).
# Usage: bash scripts/mac-linux/up.sh   (then: bash scripts/mac-linux/seed.sh)
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
step() { echo -e "${BLUE}==> $*${NC}"; }
ok()   { echo -e "${GREEN}[ok] $*${NC}"; }
warn() { echo -e "${YELLOW}[!]  $*${NC}"; }
die()  { echo -e "${RED}[error] $*${NC}"; exit 1; }

CLUSTER_NAME=ai-spaces
NAMESPACE=ai-spaces
# Pinned: kind's default node (v1.35.0) fails to boot on newer Docker Desktop / WSL2
# kernels ("could not find a log line ... Reached target Multi-User System").
NODE_IMAGE=kindest/node:v1.34.0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"   # scripts/mac-linux/ -> repo root

# ── 1. Prerequisites ──────────────────────────────────────────────────────────
step "Checking prerequisites"
command -v docker  &>/dev/null || die "Docker is not installed"
docker info        &>/dev/null || die "Docker daemon is not running. Start Docker Desktop first"
command -v kubectl &>/dev/null || die "kubectl is not installed (brew install kubectl)"

if ! command -v kind &>/dev/null; then
  step "Installing kind"
  if command -v brew &>/dev/null; then
    brew install kind
  else
    curl -Lo /usr/local/bin/kind \
      "https://kind.sigs.k8s.io/dl/v0.31.0/kind-$(uname -s | tr '[:upper:]' '[:lower:]')-amd64"
    chmod +x /usr/local/bin/kind
  fi
fi
ok "kind $(kind version)"

# ── 2. Create cluster ─────────────────────────────────────────────────────────
step "Creating kind cluster '$CLUSTER_NAME'"
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
  warn "Cluster '$CLUSTER_NAME' already exists, skipping creation"
else
  kind create cluster --name "$CLUSTER_NAME" --image "$NODE_IMAGE" \
    --config "$ROOT_DIR/infra/kind/kind-config.yml"
fi
kubectl config use-context "kind-${CLUSTER_NAME}"
ok "Cluster ready"

# ── 3. Build Docker images ────────────────────────────────────────────────────
# The two runner images use their Dockerfile.mock, so jobs run on CPU (no GPU/weights):
# SAM-3D returns a demo cube .glb, ACE-Step returns a sine-wave WAV.
step "Building Docker images (this takes a few minutes)"
docker build -q -t ai-spaces-backend:dev      "$ROOT_DIR/apps/backend"      && ok "  backend"
docker build -q -t ai-spaces-frontend:dev     "$ROOT_DIR/apps/frontend"     && ok "  frontend"
docker build -q -t ai-spaces-orchestrator:dev "$ROOT_DIR/apps/orchestrator" && ok "  orchestrator"
docker build -q -t ai-spaces-sam3d:latest \
  -f "$ROOT_DIR/apps/sam3d-runner/Dockerfile.mock"   "$ROOT_DIR/apps/sam3d-runner"   && ok "  sam3d (mock)"
docker build -q -t ai-spaces-acestep:latest \
  -f "$ROOT_DIR/apps/acestep-runner/Dockerfile.mock" "$ROOT_DIR/apps/acestep-runner" && ok "  acestep (mock)"

# ── 4. Load images into kind ──────────────────────────────────────────────────
step "Loading images into kind cluster"
for img in ai-spaces-backend:dev ai-spaces-frontend:dev ai-spaces-orchestrator:dev \
           ai-spaces-sam3d:latest ai-spaces-acestep:latest; do
  kind load docker-image "$img" --name "$CLUSTER_NAME"
done
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

# ── 7. Storage: NFS on the kind network ───────────────────────────────────────
# Artifacts live on an NFS-backed PersistentVolume (infra/k8s/nfs-local-storage.yml).
# The NFS server runs as a container joined to the same 'kind' docker network, so the
# cluster resolves it by name (ai-spaces-nfs). The cluster (step 2) must exist first,
# because it creates that 'kind' network.
step "Starting NFS server + storage"
docker compose -f "$ROOT_DIR/infra/nfs-local/docker-compose.yml" up -d
kubectl apply -f "$ROOT_DIR/infra/k8s/nfs-local-storage.yml"
ok "NFS storage ready"

# ── 8. Deploy services ────────────────────────────────────────────────────────
step "Deploying Postgres"
kubectl apply -f "$ROOT_DIR/infra/k8s/postgres.yml"
kubectl -n "$NAMESPACE" rollout status statefulset/postgres --timeout=180s

step "Deploying Keycloak (includes realm import)"
kubectl apply -k "$ROOT_DIR/infra/k8s/keycloak/"
kubectl -n "$NAMESPACE" rollout status deployment/keycloak --timeout=300s

step "Deploying backend"
kubectl apply -f "$ROOT_DIR/infra/k8s/backend.yml"
kubectl -n "$NAMESPACE" rollout status deployment/backend --timeout=300s

step "Deploying orchestrator"
kubectl apply -f "$ROOT_DIR/infra/k8s/orchestrator.yml"
kubectl -n "$NAMESPACE" rollout status deployment/orchestrator --timeout=180s

step "Deploying frontend"
kubectl apply -f "$ROOT_DIR/infra/k8s/frontend.yml"
kubectl -n "$NAMESPACE" rollout status deployment/frontend --timeout=120s

ok "All pods running"

# ── 9. Port-forwards ──────────────────────────────────────────────────────────
# Only keycloak (login) and frontend (website) are needed. nginx in the frontend pod
# proxies /api -> backend, so the browser and the seeding below reach the backend at
# http://localhost:5173/api without a separate backend forward.
step "Starting port-forwards in background"
pkill -f "kubectl port-forward.*${NAMESPACE}" 2>/dev/null || true
sleep 1
kubectl port-forward -n "$NAMESPACE" svc/keycloak 8080:8080 &>/tmp/pf-keycloak.log &
kubectl port-forward -n "$NAMESPACE" svc/frontend 5173:80   &>/tmp/pf-frontend.log  &
sleep 3
ok "Port-forwards running (logs in /tmp/pf-*.log)"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Cluster is up.${NC}"
echo ""
echo -e "  Frontend:  ${BLUE}http://localhost:5173${NC}   login: admin / admin123"
echo -e "  Keycloak:  ${BLUE}http://localhost:8080${NC}   admin: admin / admin123"
echo ""
echo -e "  Next, register the two demo Spaces (ACE-Step and SAM 3D, both run on CPU):"
echo -e "    ${BLUE}bash scripts/mac-linux/seed.sh${NC}"
echo ""
echo -e "  Restart port-forwards after reboot:"
echo -e "    kubectl port-forward -n $NAMESPACE svc/frontend 5173:80 &"
echo -e "    kubectl port-forward -n $NAMESPACE svc/keycloak 8080:8080 &"
echo ""
echo -e "  Tear everything down:  ${BLUE}bash scripts/mac-linux/down.sh${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"