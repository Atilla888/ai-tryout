#!/usr/bin/env python3
"""ACE-Step 1.5 runner using ACEStepPipeline (MPS / CPU / CUDA).

Weights are downloaded automatically from HuggingFace on first run and cached
at ~/.cache/ace-step/checkpoints. On Apple Silicon the pipeline auto-selects MPS.

Environment (injected by orchestrator):
    JOB_ID, BACKEND_API_URL, RUNNER_TOKEN
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import httpx


def _env(*names: str, default: str | None = None) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    if default is not None:
        return default
    print(f"Missing required env var: {names[0]}", file=sys.stderr)
    sys.exit(1)


def _progress(client: httpx.Client, job_id: str, percent: int, message: str) -> None:
    client.patch(
        f"/internal/jobs/{job_id}/progress",
        json={"progress_percent": percent, "message": message},
    ).raise_for_status()


def _is_cancelling(client: httpx.Client, job_id: str) -> bool:
    r = client.get(f"/internal/jobs/{job_id}")
    if r.status_code == 404:
        return True
    r.raise_for_status()
    return r.json().get("status") in {"CANCELLING", "CANCELLED"}


def _as_float(v: object, default: float) -> float:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _as_int(v: object, default: int) -> int:
    try:
        return int(float(v))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def generate(input_payload: dict, save_dir: str) -> str:
    """Run ACEStepPipeline and return the path to the generated WAV file."""
    from acestep.pipeline_ace_step import ACEStepPipeline

    prompt = str(input_payload.get("prompt") or "").strip()
    lyrics = str(input_payload.get("lyrics") or "").strip() or "[Instrumental]"
    duration = _as_float(input_payload.get("duration"), 30.0)
    steps = _as_int(input_payload.get("steps"), 20)

    checkpoint_dir = os.environ.get("ACESTEP_CHECKPOINT_DIR") or None

    pipeline = ACEStepPipeline(checkpoint_dir=checkpoint_dir)

    save_path = os.path.join(save_dir, "output.wav")
    pipeline(
        prompt=prompt,
        lyrics=lyrics,
        audio_duration=duration,
        infer_step=steps,
        format="wav",
        save_path=save_path,
    )
    return save_path


def main() -> int:
    job_id = _env("JOB_ID")
    api_base_url = _env("BACKEND_API_URL", "API_BASE_URL", default="http://localhost:8000")
    token = _env("RUNNER_TOKEN", "INTERNAL_SERVICE_TOKEN")

    client = httpx.Client(
        base_url=api_base_url.rstrip("/"),
        headers={"X-Service-Token": token},
        timeout=60.0,
    )
    try:
        resp = client.get(f"/internal/jobs/{job_id}/runner-input")
        resp.raise_for_status()
        input_payload = resp.json().get("input_payload", {}) or {}

        _progress(client, job_id, 5, "Lade Modell (erster Start: Download der Gewichte)…")
        if _is_cancelling(client, job_id):
            return 0

        _progress(client, job_id, 30, "Generiere Musik…")

        with tempfile.TemporaryDirectory() as save_dir:
            audio_path = generate(input_payload, save_dir)

            if _is_cancelling(client, job_id):
                return 0

            _progress(client, job_id, 90, "Lade Audio hoch…")
            with open(audio_path, "rb") as fh:
                client.post(
                    f"/internal/jobs/{job_id}/artifacts",
                    data={"artifact_type": "output_audio", "preview_supported": "true"},
                    files={"file": ("output.wav", fh, "audio/wav")},
                ).raise_for_status()

        client.patch(f"/internal/jobs/{job_id}/succeed").raise_for_status()
        print(f"job={job_id} completed", file=sys.stderr)
        return 0

    except Exception as exc:  # noqa: BLE001
        try:
            client.patch(
                f"/internal/jobs/{job_id}/fail",
                json={"error_code": "RUNNER_ERROR", "error_message": str(exc)[:200]},
            )
        except httpx.HTTPError:
            pass
        print(f"job={job_id} failed: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
