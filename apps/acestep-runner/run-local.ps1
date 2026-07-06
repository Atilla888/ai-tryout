# Start the orchestrator LOCALLY (no Kubernetes) with the ACE-Step runner.
#
# This uses the subprocess backend: the orchestrator runs runner.py as a child
# process for every job. No Docker / minikube / kind / cluster needed.
#
# Prereqs (see RUN_LOCAL.md): acestep + httpx installed in ..\..\venv, and the
# ACE-Step weights downloaded to the folder set in ACESTEP_CHECKPOINT_DIR below.
#
# Run the backend + Postgres first (repo README), then run this script in its own
# PowerShell tab.

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$repo = (Resolve-Path "$here\..\..").Path
$py   = "$repo\venv\Scripts\python.exe"

# --- ACE-Step settings (EDIT these) --------------------------------------------
$env:ACESTEP_CHECKPOINT_DIR = "C:\acestep-models"    # where you downloaded the weights
$env:ACESTEP_CONFIG_PATH    = "acestep-v15-base"     # model variant name from the download step
$env:ACESTEP_LM_MODEL_PATH  = "acestep-5Hz-lm-0.6B"
$env:ACESTEP_AUDIO_FORMAT   = "mp3"
$env:ACESTEP_STEPS          = "60"
$env:ACESTEP_DEVICE         = "cuda"                 # "cpu" if you have no NVIDIA GPU (slow)
# $env:ACESTEP_LM_BACKEND   = "hf"                   # uncomment if vllm won't install (native Windows)

# --- Platform wiring (usually leave as-is) -------------------------------------
$env:RUNNER_BACKEND         = "subprocess"
$env:RUNNER_SCRIPT          = "$here\runner.py"
$env:API_BASE_URL           = "http://127.0.0.1:8000"
$env:INTERNAL_SERVICE_TOKEN = "changeme-internal-token"   # must match the backend's .env
$env:CONCURRENCY_LIMIT      = "1"
$env:POLL_INTERVAL_SECONDS  = "3"

Write-Host "Starting orchestrator (subprocess backend) with ACE-Step runner at $env:RUNNER_SCRIPT"
& $py "$repo\apps\orchestrator\main.py"
