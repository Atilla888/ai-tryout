#!/usr/bin/env python3
"""GPU-free stand-in for the ACE-Step runner, for demoing the pipeline locally.

It follows the *exact* same runner contract and output shape as ``runner.py``
(uploads an ``output_audio`` artifact so the frontend plays it inline) — the only
difference is that instead of running the ACE-Step model it synthesizes a short
WAV tone with the Python standard library. Use it to prove the end-to-end flow
(form -> job -> audio result -> player) on a machine without an NVIDIA GPU.

Wire it in exactly like the real runner: RUNNER_BACKEND=subprocess and
RUNNER_SCRIPT pointing at this file.
"""
from __future__ import annotations

import io
import math
import struct
import sys
import time
import wave

from runner import _env, _is_cancelling, _progress  # reuse the verified contract helpers

import httpx

SAMPLE_RATE = 44100
DURATION_SECONDS = 3.0


def synthesize_wav(prompt: str) -> bytes:
    """Make a short sine-tone WAV. Pitch varies with the prompt so different
    prompts sound different — purely cosmetic, no model involved."""
    base_freq = 220.0 + (len(prompt) % 24) * 15.0  # 220–565 Hz depending on prompt
    n_samples = int(SAMPLE_RATE * DURATION_SECONDS)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit PCM
        wav.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for i in range(n_samples):
            # simple fade in/out so it doesn't click
            env = min(1.0, i / 2000, (n_samples - i) / 2000)
            sample = env * 0.6 * math.sin(2 * math.pi * base_freq * (i / SAMPLE_RATE))
            frames += struct.pack("<h", int(sample * 32767))
        wav.writeframes(frames)
    return buf.getvalue()


def main() -> int:
    job_id = _env("JOB_ID")
    api_base_url = _env("BACKEND_API_URL", "API_BASE_URL", default="http://localhost:8000")
    token = _env("RUNNER_TOKEN", "INTERNAL_SERVICE_TOKEN")

    client = httpx.Client(
        base_url=api_base_url.rstrip("/"),
        headers={"X-Service-Token": token},
        timeout=30.0,
    )
    try:
        resp = client.get(f"/internal/jobs/{job_id}/runner-input")
        resp.raise_for_status()
        input_payload = resp.json().get("input_payload", {}) or {}
        prompt = str(input_payload.get("prompt", "") or "")

        for percent, msg in ((5, "Warming up…"), (45, "Synthesizing…"), (85, "Encoding audio…")):
            if _is_cancelling(client, job_id):
                print(f"job={job_id} cancelled", file=sys.stderr)
                return 0
            _progress(client, job_id, percent, msg)
            time.sleep(0.3)

        audio_bytes = synthesize_wav(prompt)
        client.post(
            f"/internal/jobs/{job_id}/artifacts",
            data={"artifact_type": "output_audio", "preview_supported": "true"},
            files={"file": ("mock-acestep.wav", audio_bytes, "audio/wav")},
        ).raise_for_status()

        client.patch(f"/internal/jobs/{job_id}/succeed").raise_for_status()
        print(f"job={job_id} completed (mock audio)", file=sys.stderr)
        return 0
    except httpx.HTTPError as exc:
        try:
            client.patch(
                f"/internal/jobs/{job_id}/fail",
                json={"error_code": "RUNNER_ERROR", "error_message": str(exc)[:100]},
            )
        except httpx.HTTPError:
            pass
        print(f"job={job_id} failed: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
