<#
.SYNOPSIS
  Bring up the whole AI-Spaces stack on a local kind cluster in one command.

.DESCRIPTION
  Creates the kind cluster (auto-retries the flaky first boot), starts the NFS
  server, generates secrets if missing, builds and loads the images, applies all
  manifests in order, and waits until everything is ready. Safe to re-run.

.EXAMPLE
  ./scripts/windows/up.ps1
  ./scripts/windows/up.ps1 -SkipBuild      # redeploy without rebuilding images
#>
[CmdletBinding()]
param(
  [string]$ClusterName = "ai-spaces",
  [switch]$SkipBuild,
  # Node image is pinned to v1.34.0 because the kind default (v1.35.0) fails to boot on
  # newer WSL2 kernels ("could not find a log line ... Reached target Multi-User System").
  # Override if you need a different one, e.g. -NodeImage kindest/node:v1.31.6.
  [string]$NodeImage = "kindest/node:v1.34.0"
)

# NOTE: we deliberately do NOT set $ErrorActionPreference='Stop'. kind/kubectl/docker
# write normal status text to stderr, which under 'Stop' becomes a fatal error in
# Windows PowerShell 5.1. Instead we check $LASTEXITCODE explicitly via Run().
$ns = "ai-spaces"

# Repo root = two levels up from this script (scripts/windows/ -> repo root)
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

function Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "  OK  $msg" -ForegroundColor Green }

# Run a native command and abort if it returns a non-zero exit code.
# NOTE: plain function with $args (no param block) so dashed flags like `-d` pass through
# verbatim. A param()/[Parameter()] block turns this into an advanced function, which would
# steal `-d` (-> -Debug), `-v` (-> -Verbose), etc. from the wrapped command.
function Run {
  $exe  = $args[0]
  $rest = @($args | Select-Object -Skip 1)
  & $exe @rest
  if ($LASTEXITCODE -ne 0) { throw "Command failed (exit $LASTEXITCODE): $($args -join ' ')" }
}

# --- Preflight ---------------------------------------------------------------
Step "Preflight"
foreach ($tool in "docker","kind","kubectl") {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
    throw "'$tool' is not installed or not on PATH."
  }
}
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker isn't running. Start Docker Desktop and re-run." }
Ok "docker, kind, kubectl present; Docker is running"

# --- 1. Cluster (with retry for the transient WSL/systemd boot failure) ------
Step "1. Cluster '$ClusterName'"
$existing = (kind get clusters 2>&1) | ForEach-Object { "$_".Trim() }
if ($existing -contains $ClusterName) {
  Ok "cluster already exists"
} else {
  $imageArgs = @()
  if ($NodeImage) { $imageArgs = @("--image", $NodeImage); Write-Host "  Using pinned node image: $NodeImage" }
  $created = $false
  for ($try = 1; $try -le 3 -and -not $created; $try++) {
    Write-Host "  Creating cluster (attempt $try/3)..."
    kind create cluster --name $ClusterName --config infra/kind/kind-config.yml @imageArgs
    if ($LASTEXITCODE -eq 0) { $created = $true; break }
    Write-Host "  Boot failed (known transient issue). Cleaning up and retrying..." -ForegroundColor Yellow
    kind delete cluster --name $ClusterName *> $null
    if ($try -eq 1) { Write-Host "  Tip: if this keeps failing, run 'wsl --shutdown' and restart Docker Desktop." -ForegroundColor Yellow }
    Start-Sleep -Seconds 5
  }
  if (-not $created) { throw "Cluster failed to start after 3 attempts. Run 'wsl --shutdown', restart Docker Desktop, and try again." }
  Ok "cluster created"
}
kubectl config use-context "kind-$ClusterName" *> $null

# --- 2. NFS server (artifact storage, on the kind network) -------------------
Step "2. NFS storage server"
Run docker compose -f infra/nfs-local/docker-compose.yml up -d
Ok "ai-spaces-nfs running on the 'kind' network"

# --- 3. Secrets (generate if missing) ----------------------------------------
Step "3. Secrets"
$secretsPath = "infra/k8s/secrets/secrets.yml"
if (Test-Path $secretsPath) {
  Ok "secrets.yml already present (leaving as-is)"
} else {
  function New-Hex($bytes) { -join ((1..$bytes) | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) }) }
  $dbPass = New-Hex 24
  $kcPass = New-Hex 24
  $token  = New-Hex 32
  New-Item -ItemType Directory -Force -Path "infra/k8s/secrets" | Out-Null
  @"
apiVersion: v1
kind: Secret
metadata:
  name: postgres-secret
  namespace: ai-spaces
type: Opaque
stringData:
  POSTGRES_USER: aispacesuser
  POSTGRES_PASSWORD: $dbPass
  POSTGRES_DB: aispaces
---
apiVersion: v1
kind: Secret
metadata:
  name: keycloak-secret
  namespace: ai-spaces
type: Opaque
stringData:
  KC_BOOTSTRAP_ADMIN_USERNAME: admin
  KC_BOOTSTRAP_ADMIN_PASSWORD: $kcPass
---
apiVersion: v1
kind: Secret
metadata:
  name: backend-secret
  namespace: ai-spaces
type: Opaque
stringData:
  DATABASE_URL: postgresql+asyncpg://aispacesuser:$dbPass@postgres:5432/aispaces
  ALEMBIC_DATABASE_URL: postgresql+psycopg://aispacesuser:$dbPass@postgres:5432/aispaces
  INTERNAL_SERVICE_TOKEN: $token
"@ | Set-Content -Path $secretsPath -Encoding utf8
  Ok "generated $secretsPath with fresh random values"
}

# --- 4. Build images ---------------------------------------------------------
# The two runner images use their Dockerfile.mock so jobs run on CPU (no GPU/weights):
# SAM-3D returns a demo cube .glb, ACE-Step returns a sine-wave WAV.
$images = @(
  @{ tag = "ai-spaces-backend:dev";      buildArgs = @("-t","ai-spaces-backend:dev","apps/backend") },
  @{ tag = "ai-spaces-orchestrator:dev"; buildArgs = @("-t","ai-spaces-orchestrator:dev","apps/orchestrator") },
  @{ tag = "ai-spaces-frontend:dev";     buildArgs = @("-t","ai-spaces-frontend:dev","apps/frontend") },
  @{ tag = "ai-spaces-sam3d:latest";     buildArgs = @("-t","ai-spaces-sam3d:latest","-f","apps/sam3d-runner/Dockerfile.mock","apps/sam3d-runner") },
  @{ tag = "ai-spaces-acestep:latest";   buildArgs = @("-t","ai-spaces-acestep:latest","-f","apps/acestep-runner/Dockerfile.mock","apps/acestep-runner") }
)
if ($SkipBuild) {
  Step "4. Build images (skipped)"
} else {
  Step "4. Build images"
  foreach ($img in $images) {
    Write-Host "  Building $($img.tag)..."
    Run docker build @($img.buildArgs)
  }
  Ok "5 images built"
}

# --- 5. Load images into kind ------------------------------------------------
Step "5. Load images into kind"
foreach ($img in $images) {
  Run kind load docker-image $img.tag --name $ClusterName
}
Ok "images loaded into the cluster"

# --- 6. Apply manifests (in dependency order) --------------------------------
Step "6. Apply manifests"
Run kubectl apply -f infra/k8s/namespace.yml
Run kubectl apply -f infra/k8s/secrets/secrets.yml
Run kubectl apply -f infra/k8s/nfs-local-storage.yml
Run kubectl apply -f infra/k8s/postgres.yml
Run kubectl apply -k infra/k8s/keycloak/
Run kubectl apply -f infra/k8s/backend.yml
Run kubectl apply -f infra/k8s/orchestrator.yml
Run kubectl apply -f infra/k8s/frontend.yml
Ok "all manifests applied"

# --- 7. Wait for readiness ---------------------------------------------------
Step "7. Wait for rollout (Keycloak is slowest on first boot)"
Run kubectl rollout status statefulset/postgres   -n $ns --timeout=180s
Run kubectl rollout status deployment/keycloak     -n $ns --timeout=300s
Run kubectl rollout status deployment/backend      -n $ns --timeout=300s
Run kubectl rollout status deployment/orchestrator -n $ns --timeout=180s
Run kubectl rollout status deployment/frontend     -n $ns --timeout=180s
Ok "everything is ready"

# --- Done --------------------------------------------------------------------
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host " AI-Spaces is up. Open it with these port-forwards" -ForegroundColor Green
Write-Host " (each in its own terminal, leave running):" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host @"
  kubectl port-forward svc/keycloak 8080:8080 -n ai-spaces
  kubectl port-forward svc/frontend 5173:80   -n ai-spaces

(nginx in the frontend pod proxies /api -> backend, so no backend forward is needed.)

Then open  http://localhost:5173  and log in as  admin / admin123
Seed the demo spaces:  ./scripts/windows/seed.ps1   (manages its own forwards)
Tear everything down:  ./scripts/windows/down.ps1
"@
