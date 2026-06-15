#!/usr/bin/env python3
"""Fake model runner for Sprint 1. Simulates progress, artifact upload, and completion."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx

PROGRESS_STEPS: tuple[tuple[int, str], ...] = (
    (20, "Processing… 20%"),
    (40, "Processing… 40%"),
    (60, "Processing… 60%"),
    (80, "Processing… 80%"),
)
STEP_DELAY_SECONDS = 2


def _env(name: str) -> str:
    """Reads a required environment variable and exits the process if it is not set."""
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def _simulate_failure() -> bool:
    """Returns True if SIMULATE_FAILURE is set to a truthy value, used in tests to
    exercise the failure path without a real model."""
    return os.environ.get("SIMULATE_FAILURE", "").strip().lower() in {"1", "true", "yes", "on"}


def _headers(token: str) -> dict[str, str]:
    return {"X-Service-Token": token}


def _patch_progress(client: httpx.Client, job_id: str, percent: int, message: str) -> None:
    response = client.patch(
        f"/internal/jobs/{job_id}/progress",
        json={"progress_percent": percent, "message": message},
    )
    response.raise_for_status()


def _upload_artifact(client: httpx.Client, job_id: str) -> None:
    """Uploads dummy_result.txt as the job output artifact. Falls back to a hardcoded
    string if the file is missing, so tests can run without the file present."""
    dummy_path = Path(__file__).with_name("dummy_result.txt")
    content = dummy_path.read_bytes() if dummy_path.is_file() else b"AI Spaces fake runner output\n"
    response = client.post(
        f"/internal/jobs/{job_id}/artifacts",
        data={"artifact_type": "text", "preview_supported": "true"},
        files={"file": ("result.txt", content, "text/plain")},
    )
    response.raise_for_status()


def _patch_succeed(client: httpx.Client, job_id: str) -> None:
    response = client.patch(f"/internal/jobs/{job_id}/succeed")
    response.raise_for_status()


def _patch_fail(client: httpx.Client, job_id: str) -> None:
    response = client.patch(
        f"/internal/jobs/{job_id}/fail",
        json={"error_code": "SIMULATED_FAILURE", "error_message": "Fake runner simulated failure"},
    )
    response.raise_for_status()


def run() -> int:
    """Main runner logic. Sends progress updates, uploads one output artifact, then
    marks the job as succeeded (or failed if SIMULATE_FAILURE is set).
    Returns 0 on success, 1 on simulated failure."""
    job_id = _env("JOB_ID")
    api_base_url = _env("API_BASE_URL").rstrip("/")
    token = _env("INTERNAL_SERVICE_TOKEN")

    with httpx.Client(base_url=api_base_url, headers=_headers(token), timeout=30.0) as client:
        if _simulate_failure():
            print(f"[fake-runner] job={job_id} simulating failure")
            _patch_fail(client, job_id)
            return 1

        for percent, message in PROGRESS_STEPS:
            print(f"[fake-runner] job={job_id} progress={percent}%")
            _patch_progress(client, job_id, percent, message)
            time.sleep(STEP_DELAY_SECONDS)

        print(f"[fake-runner] job={job_id} uploading artifact")
        _upload_artifact(client, job_id)

        print(f"[fake-runner] job={job_id} marking succeeded")
        _patch_succeed(client, job_id)

    print(f"[fake-runner] job={job_id} done")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
