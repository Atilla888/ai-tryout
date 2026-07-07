#!/usr/bin/env bash
# Register the two demo Spaces (ACE-Step + SAM 3D) into a running deployment.
# Both use their CPU mock runner image, so jobs run without a GPU.
# Needs the keycloak (:8080) and frontend (:5173) port-forwards from up.sh running.
# Usage: bash scripts/mac-linux/seed.sh
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
step() { echo -e "${BLUE}==> $*${NC}"; }
ok()   { echo -e "${GREEN}[ok] $*${NC}"; }
warn() { echo -e "${YELLOW}[!]  $*${NC}"; }
die()  { echo -e "${RED}[error] $*${NC}"; exit 1; }

NAMESPACE=ai-spaces

# ── Admin token (waits for Keycloak to be reachable) ──────────────────────────
step "Getting an admin token from Keycloak"
TOKEN=""
for i in $(seq 1 24); do
  TOKEN=$(curl -sf -X POST \
    "http://localhost:8080/realms/ai-spaces/protocol/openid-connect/token" \
    -d "client_id=ai-spaces-frontend&grant_type=password&username=admin&password=admin123" \
    2>/dev/null \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || true)
  [ -n "$TOKEN" ] && break
  echo "  Waiting for Keycloak on :8080... ($i/24)  (is the port-forward running?)"
  sleep 5
done
[ -n "$TOKEN" ] || die "Couldn't reach Keycloak on :8080. Run 'bash scripts/mac-linux/up.sh' first (it starts the port-forwards)."
ok "Admin token acquired"

# ── Register the two demo spaces (via the frontend nginx proxy /api) ──────────
step "Registering demo spaces via the backend API"
register_space() {  # $1 = label, $2 = JSON body
  curl -sf -X POST "http://localhost:5173/api/creator/spaces" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "$2" &>/dev/null && ok "  $1 registered" \
    || warn "  $1: already exists or API error (safe to ignore)"
}

register_space "ACE-Step (text -> music)" '{
  "slug":"acestep-music","name":"ACE-Step 1.5 - Text to Music",
  "description":"Generate a music track from a style prompt. Mock mode returns a sine-wave WAV.",
  "task_type":"Audio","input_types":["text"],"output_types":["audio"],
  "container_image":"ai-spaces-acestep:latest","visibility":"PUBLIC","status":"PUBLISHED",
  "runner_config":{},
  "ui_config":{"inputs":[
    {"name":"prompt","type":"text","label":"Style / prompt","required":true,"maxLength":512},
    {"name":"lyrics","type":"text","label":"Lyrics (optional)","required":false,"maxLength":4096}
  ]}
}'

register_space "SAM 3D (image -> 3D)" '{
  "slug":"sam-3d-objects","name":"3D Generator - SAM 3D Objects",
  "description":"Upload a photo and get a 3D model (.glb). Mock mode returns a blue cube.",
  "task_type":"3D","input_types":["image"],"output_types":["3d"],
  "container_image":"ai-spaces-sam3d:latest","visibility":"PUBLIC","status":"PUBLISHED",
  "runner_config":{},
  "ui_config":{"inputs":[
    {"name":"image","type":"image_upload","label":"Input Image","required":true,
     "mime_types":["image/png","image/jpeg","image/webp"],"max_size_mb":20}
  ]}
}'

echo ""
ok "Done. Open http://localhost:5173 and both Spaces should appear (both run on CPU)."