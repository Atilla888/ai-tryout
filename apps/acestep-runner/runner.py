#!/usr/bin/env python3
"""ACE-Step 1.5 text-to-music runner for the AI-Spaces platform.

It follows the same runner contract as ``apps/orchestrator/fake_runner.py`` — the
only difference is that the "work" step actually runs the ACE-Step 1.5 model
instead of sleeping:

1. read the job id and backend connection details from the environment;
2. fetch the job input payload (the space's form fields);
3. report progress (the first update also flips STARTING -> RUNNING);
4. run ACE-Step to synthesize a track;
5. upload the audio as an ``output_audio`` artifact (the type the frontend's
   ArtifactViewer renders with a <audio> player);
6. report success (or failure).

Model loading is heavy, so we send an early progress ping *before* loading so the
job leaves STARTING promptly. One container == one job (the platform launches a
fresh K8s Job per job), so we load the model, generate once, and exit.

Model weights are expected on a mounted volume at ``ACESTEP_CHECKPOINT_DIR``
(see the K8s runner_config wiring in ``apps/orchestrator/runner_backends.py``),
otherwise ACE-Step would re-download several GB on every job.
"""
from __future__ import annotations

import os
import sys
import tempfile

import httpx

# ---------------------------------------------------------------------------
# Runner contract helpers (identical shape to fake_runner.py)
# ---------------------------------------------------------------------------

# Extension + MIME for each ACE-Step output format. mp3 is the default: small
# and playable by every browser <audio> element.
AUDIO_FORMATS = {
    "mp3": (".mp3", "audio/mpeg"),
    "wav": (".wav", "audio/wav"),
    "wav32": (".wav", "audio/wav"),
    "flac": (".flac", "audio/flac"),
    "opus": (".opus", "audio/ogg"),
    "aac": (".aac", "audio/aac"),
}


def _env(*names: str, default: str | None = None) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    if default is not None:
        return default
    print(f"Missing required environment variable: {names[0]}", file=sys.stderr)
    sys.exit(1)


def _is_cancelling(client: httpx.Client, job_id: str) -> bool:
    response = client.get(f"/internal/jobs/{job_id}")
    if response.status_code == 404:
        return True
    response.raise_for_status()
    return response.json().get("status") in {"CANCELLING", "CANCELLED"}


def _progress(client: httpx.Client, job_id: str, percent: int, message: str) -> None:
    client.patch(
        f"/internal/jobs/{job_id}/progress",
        json={"progress_percent": percent, "message": message},
    ).raise_for_status()


def _as_float(value: object, default: float) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _as_int(value: object, default: int) -> int:
    try:
        return int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# ACE-Step 1.5 inference (the only model-specific part)
# ---------------------------------------------------------------------------

def generate_audio(input_payload: dict, save_dir: str) -> tuple[str, str, str]:
    """Run ACE-Step 1.5 and return (file_path, content_type, file_name).

    ``input_payload`` holds the space's submitted form fields. Field names must
    match the space ``ui_config`` (see space.json): prompt, lyrics, duration,
    steps.  Model + runtime knobs come from environment variables that the
    orchestrator/runner_config feeds in.

    The imports live inside the function so the contract code above stays
    importable (and unit-testable) on a machine without the heavy ML deps.
    """
    # Documented ACE-Step 1.5 entry points (docs/en/INFERENCE.md). Pin the
    # acestep version in requirements.txt so these stay stable.
    from acestep.handler import AceStepHandler
    from acestep.llm_inference import LLMHandler
    from acestep.inference import GenerationConfig, GenerationParams, generate_music

    checkpoint_dir = _env("ACESTEP_CHECKPOINT_DIR", default="/models")
    config_path = _env("ACESTEP_CONFIG_PATH", default="acestep-v15-base")
    lm_model_path = _env("ACESTEP_LM_MODEL_PATH", default="acestep-5Hz-lm-0.6B")
    device = _env("ACESTEP_DEVICE", default="cuda")
    audio_format = _env("ACESTEP_AUDIO_FORMAT", default="mp3").lower()
    ext, content_type = AUDIO_FORMATS.get(audio_format, AUDIO_FORMATS["mp3"])

    dit_handler = AceStepHandler()
    dit_handler.initialize_service(
        project_root=checkpoint_dir,
        config_path=config_path,
        device=device,
    )
    llm_handler = LLMHandler()
    llm_handler.initialize(
        checkpoint_dir=checkpoint_dir,
        lm_model_path=lm_model_path,
        backend=_env("ACESTEP_LM_BACKEND", default="vllm"),
        device=device,
    )

    lyrics = str(input_payload.get("lyrics", "") or "").strip()
    params = GenerationParams(
        task_type="text2music",
        caption=str(input_payload.get("prompt", "") or "").strip(),
        lyrics=lyrics or "[Instrumental]",
        instrumental=not lyrics,
        duration=_as_float(input_payload.get("duration"), -1.0),
        inference_steps=_as_int(input_payload.get("steps"), _as_int(os.environ.get("ACESTEP_STEPS"), 8)),
        guidance_scale=_as_float(os.environ.get("ACESTEP_GUIDANCE"), 7.0),
        seed=_as_int(input_payload.get("seed"), -1),
    )
    config = GenerationConfig(batch_size=1, audio_format=audio_format)

    result = generate_music(dit_handler, llm_handler, params, config, save_dir=save_dir)
    if not getattr(result, "success", False) or not result.audios:
        raise RuntimeError(getattr(result, "error", "ACE-Step generation failed"))

    src_path = result.audios[0]["path"]
    file_name = f"acestep{ext}"
    return src_path, content_type, file_name


# ---------------------------------------------------------------------------
# Main contract loop
# ---------------------------------------------------------------------------

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
        # 1 + 2: fetch the submitted form payload.
        resp = client.get(f"/internal/jobs/{job_id}/runner-input")
        resp.raise_for_status()
        input_payload = resp.json().get("input_payload", {}) or {}

        # 3: early ping flips STARTING -> RUNNING before the slow model load.
        _progress(client, job_id, 5, "Loading model…")
        if _is_cancelling(client, job_id):
            print(f"job={job_id} cancelled before start", file=sys.stderr)
            return 0

        # 4: run the model.
        _progress(client, job_id, 30, "Generating music…")
        with tempfile.TemporaryDirectory() as save_dir:
            src_path, content_type, file_name = generate_audio(input_payload, save_dir)

            if _is_cancelling(client, job_id):
                print(f"job={job_id} cancelled after generation", file=sys.stderr)
                return 0

            # 5: upload the track as an output_audio artifact (frontend plays it).
            _progress(client, job_id, 90, "Uploading result…")
            with open(src_path, "rb") as fh:
                client.post(
                    f"/internal/jobs/{job_id}/artifacts",
                    data={"artifact_type": "output_audio", "preview_supported": "true"},
                    files={"file": (file_name, fh, content_type)},
                ).raise_for_status()

        # 6: report success.
        client.patch(f"/internal/jobs/{job_id}/succeed").raise_for_status()
        print(f"job={job_id} completed", file=sys.stderr)
        return 0
    except httpx.HTTPError as exc:
        _report_failure(client, job_id, "RUNNER_ERROR", str(exc))
        print(f"job={job_id} failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - any model error must fail the job, not hang it
        _report_failure(client, job_id, "MODEL_ERROR", str(exc))
        print(f"job={job_id} failed: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()


def _report_failure(client: httpx.Client, job_id: str, error_code: str, error_message: str) -> None:
    """Best-effort failure report so the job doesn't hang in RUNNING."""
    try:
        client.patch(
            f"/internal/jobs/{job_id}/fail",
            json={"error_code": error_code, "error_message": error_message[:100]},
        )
    except httpx.HTTPError:
        pass


if __name__ == "__main__":
    sys.exit(main())
