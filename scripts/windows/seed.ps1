<#
.SYNOPSIS
  Seed the two demo spaces (SAM-3D + ACE-Step) into a running deployment.

.DESCRIPTION
  Reaches the backend through the frontend's nginx proxy (http://localhost:5173/api),
  so it reuses the same port-forwards you use for browsing, with no dedicated backend
  forward needed. Self-contained: if Keycloak (:8080) or the frontend (:5173) aren't
  already reachable, it starts temporary port-forwards for the seeding and tears them
  down afterward. So you can just run this any time after ./scripts/windows/up.ps1.
#>
[CmdletBinding()]
param(
  [string]$KeycloakUrl = "http://localhost:8080",
  # Backend is reached via the frontend nginx proxy: /api/ -> backend:8000
  [string]$BackendUrl  = "http://localhost:5173/api",
  [string]$Namespace   = "ai-spaces"
)

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

$startedJobs = @()

function Test-Port([int]$port) {
  $c = New-Object System.Net.Sockets.TcpClient
  try { $c.Connect("localhost", $port); return $c.Connected }
  catch { return $false }
  finally { $c.Close() }
}

function Ensure-Forward([string]$svc, [int]$localPort, [int]$remotePort) {
  if (Test-Port $localPort) { Write-Host "  $svc already reachable on :$localPort" -ForegroundColor DarkGray; return }
  Write-Host "  starting temporary port-forward svc/$svc ${localPort}:${remotePort}..." -ForegroundColor DarkGray
  $job = Start-Job -ScriptBlock {
    param($s, $l, $r, $n)
    kubectl port-forward "svc/$s" "${l}:${r}" -n $n
  } -ArgumentList $svc, $localPort, $remotePort, $Namespace
  $script:startedJobs += $job
  for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 400
    if (Test-Port $localPort) { return }
  }
  throw "port-forward for $svc did not become ready on :$localPort"
}

try {
  Write-Host "Ensuring Keycloak and the frontend proxy are reachable..." -ForegroundColor Cyan
  Ensure-Forward "keycloak" 8080 8080
  Ensure-Forward "frontend" 5173 80

  Write-Host "Getting admin token from Keycloak..." -ForegroundColor Cyan
  $resp = Invoke-RestMethod -Method Post -Uri "$KeycloakUrl/realms/ai-spaces/protocol/openid-connect/token" `
    -Body @{ grant_type = "password"; client_id = "ai-spaces-frontend"; username = "admin"; password = "admin123" }
  $token = $resp.access_token
  $headers = @{ Authorization = "Bearer $token" }

  # Both spaces use their mock runner image (built + kind-loaded by up.ps1), so both
  # run on CPU: ACE-Step returns a sine-wave WAV, SAM-3D a demo cube .glb.
  $spaces = @(
    @{
      slug = "acestep-music"; name = "ACE-Step 1.5 - Text to Music"
      description = "Generate a music track from a style prompt. Mock mode returns a sine-wave WAV."
      task_type = "Audio"; input_types = @("text"); output_types = @("audio")
      container_image = "ai-spaces-acestep:latest"; visibility = "PUBLIC"; status = "PUBLISHED"
      runner_config = @{}
      ui_config = @{ inputs = @(
        @{ name = "prompt"; type = "text"; label = "Style / prompt"; required = $true;  maxLength = 512 },
        @{ name = "lyrics"; type = "text"; label = "Lyrics (optional)"; required = $false; maxLength = 4096 }
      ) }
    },
    @{
      slug = "sam-3d-objects"; name = "3D Generator - SAM 3D Objects"
      description = "Upload a photo and get a 3D model (.glb). Mock mode returns a blue cube."
      task_type = "3D"; input_types = @("image"); output_types = @("3d")
      container_image = "ai-spaces-sam3d:latest"; visibility = "PUBLIC"; status = "PUBLISHED"
      runner_config = @{}
      ui_config = @{ inputs = @(
        @{ name = "image"; type = "image_upload"; label = "Input Image"; required = $true;
           mime_types = @("image/png","image/jpeg","image/webp"); max_size_mb = 20 }
      ) }
    }
  )
  foreach ($space in $spaces) {
    Write-Host "Creating space '$($space.name)' ..." -ForegroundColor Cyan
    $bytes = [System.Text.Encoding]::UTF8.GetBytes(($space | ConvertTo-Json -Depth 8))
    try {
      $created = Invoke-RestMethod -Method Post -Uri "$BackendUrl/creator/spaces" -Headers $headers `
        -ContentType "application/json" -Body $bytes
      Write-Host "  OK  '$($created.name)'  (id $($created.id))" -ForegroundColor Green
    } catch {
      $status = ""
      $body = ""
      if ($_.Exception.Response) {
        try { $status = [int]$_.Exception.Response.StatusCode } catch {}
        try {
          $sr = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
          $body = $sr.ReadToEnd()
        } catch {}
      }
      if ($status -eq 409) { Write-Host "  Skipped (already exists)" -ForegroundColor Yellow }
      else { throw "Failed to create space '$($space.name)' (HTTP $status): $body" }
    }
  }

  Write-Host "`nDone. Refresh http://localhost:5173 - both spaces should appear (both run on CPU)." -ForegroundColor Green
}
finally {
  if ($startedJobs.Count -gt 0) {
    Write-Host "Stopping temporary port-forwards..." -ForegroundColor DarkGray
    $startedJobs | ForEach-Object { Stop-Job $_ -ErrorAction SilentlyContinue; Remove-Job $_ -Force -ErrorAction SilentlyContinue }
  }
}
