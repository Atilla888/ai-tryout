#!/usr/bin/env bash
# Tear down the AI-Spaces kind cluster and the NFS server (Mac/Linux).
# Usage:
#   bash scripts/mac-linux/down.sh           # delete cluster + stop NFS (keep artifacts)
#   bash scripts/mac-linux/down.sh --wipe    # also delete the NFS data volume (artifacts)
set -euo pipefail

BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
CLUSTER_NAME=ai-spaces
NAMESPACE=ai-spaces
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"   # scripts/mac-linux/ -> repo root

echo -e "${BLUE}==> Stopping port-forwards${NC}"
pkill -f "kubectl port-forward.*${NAMESPACE}" 2>/dev/null || true

echo -e "${BLUE}==> Deleting kind cluster '${CLUSTER_NAME}'${NC}"
kind delete cluster --name "$CLUSTER_NAME"

echo -e "${BLUE}==> Stopping NFS server${NC}"
if [ "${1:-}" = "--wipe" ]; then
  docker compose -f "$ROOT_DIR/infra/nfs-local/docker-compose.yml" down -v
  echo -e "${YELLOW}  NFS data volume wiped.${NC}"
else
  docker compose -f "$ROOT_DIR/infra/nfs-local/docker-compose.yml" down
fi

echo -e "${GREEN}Done.${NC}"