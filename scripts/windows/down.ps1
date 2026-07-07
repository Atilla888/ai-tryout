<#
.SYNOPSIS
  Tear down the AI-Spaces kind cluster and the NFS server.

.EXAMPLE
  ./scripts/windows/down.ps1              # delete cluster + stop NFS (keep artifacts)
  ./scripts/windows/down.ps1 -Wipe        # also delete the NFS data volume (artifacts)
#>
[CmdletBinding()]
param(
  [string]$ClusterName = "ai-spaces",
  [switch]$Wipe
)

# No global 'Stop': kind/docker write status to stderr, which would fault under Stop
# in Windows PowerShell 5.1.
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

Write-Host "Deleting kind cluster '$ClusterName'..." -ForegroundColor Cyan
kind delete cluster --name $ClusterName

Write-Host "Stopping NFS server..." -ForegroundColor Cyan
if ($Wipe) {
  docker compose -f infra/nfs-local/docker-compose.yml down -v
  Write-Host "  NFS data volume wiped." -ForegroundColor Yellow
} else {
  docker compose -f infra/nfs-local/docker-compose.yml down
}

Write-Host "Done." -ForegroundColor Green
