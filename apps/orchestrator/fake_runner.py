#!/usr/bin/env python3
"""Self-contained reference/fake runner used by the subprocess backend and tests.

It follows the platform runner contract end to end:

1. read the job id and backend connection details from the environment;
2. fetch the job input, including any uploaded INPUT files (D4);
3. download and "use" those input files (here: read their sizes);
4. report progress;
5. upload a result artifact summarizing the inputs;
6. report success.

It cooperatively stops if the job has been moved to CANCELLING/CANCELLED while it
was working — the orchestrator also force-terminates it, so cancellation works
either way. Real model runners follow the same shape using the SDK in
``runner-template/`` instead of inlining the HTTP calls.
"""
from __future__ import annotations

import json
import os
import sys
import time

import httpx

PROGRESS_STEPS = (20, 40, 60, 80)


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
        # 1 + 2: fetch input payload and input file references.
        resp = client.get(f"/internal/jobs/{job_id}/runner-input")
        resp.raise_for_status()
        runner_input = resp.json()
        input_payload = runner_input.get("input_payload", {})
        input_artifacts = runner_input.get("input_artifacts", [])

        # 3: download and use the input files.
        consumed_inputs = []
        for artifact in input_artifacts:
            file_resp = client.get(artifact["content_url"])
            file_resp.raise_for_status()
            consumed_inputs.append(
                {
                    "field_name": artifact.get("field_name"),
                    "file_name": artifact["file_name"],
                    "bytes_read": len(file_resp.content),
                }
            )

        # 4: report progress (the first update also flips STARTING -> RUNNING).
        for percent in PROGRESS_STEPS:
            if _is_cancelling(client, job_id):
                print(f"job={job_id} cancelled, stopping", file=sys.stderr)
                return 0
            client.patch(
                f"/internal/jobs/{job_id}/progress",
                json={"progress_percent": percent, "message": f"Processing… {percent}%"},
            ).raise_for_status()
            time.sleep(0.2)

        # 5: upload a result artifact summarizing what we received.
        summary = {
            "prompt": {k: v for k, v in input_payload.items() if k != "input_artifacts"},
            "inputs_used": consumed_inputs,
            "message": "AI Spaces fake runner output",
        }
        client.post(
            f"/internal/jobs/{job_id}/artifacts",
            data={"artifact_type": "text", "preview_supported": "true"},
            files={"file": ("result.json", json.dumps(summary, indent=2).encode(), "application/json")},
        ).raise_for_status()

        # 6: report success.
        client.patch(f"/internal/jobs/{job_id}/succeed").raise_for_status()
        print(f"job={job_id} completed", file=sys.stderr)
        return 0
    except httpx.HTTPError as exc:
        # Best-effort failure report so the job doesn't hang in RUNNING.
        try:
            client.patch(
                f"/internal/jobs/{job_id}/fail",
                json={"error_code": "RUNNER_ERROR", "error_message": str(exc)},
            )
        except httpx.HTTPError:
            pass
        print(f"job={job_id} failed: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
