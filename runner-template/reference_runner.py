#!/usr/bin/env python3
"""Reference model runner built on the AI-Spaces runner SDK.

This is the minimal, copy-me example for space creators. Replace the body of
``run_inference`` with your model code; the surrounding contract (input fetch,
progress, artifact upload, success/failure) is handled by the SDK.

It runs as a Kubernetes Job (or local subprocess) with the environment the
orchestrator injects: JOB_ID, SPACE_ID, BACKEND_API_URL, RUNNER_TOKEN,
INPUT_REFERENCE.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from runner_sdk import Runner, RunnerInput


def run_inference(runner: Runner, job: RunnerInput, work_dir: Path) -> Path:
    """Replace this with real model inference. Returns the path to the output file.

    The reference implementation echoes the prompt and the names/sizes of any
    uploaded input files so the end-to-end pipeline is verifiable without a GPU.
    """
    runner.report_progress(10, "Reading inputs")
    input_paths = runner.download_inputs(work_dir / "inputs")

    runner.report_progress(60, "Running model")
    result = {
        "prompt": {k: v for k, v in job.input_payload.items() if k != "input_artifacts"},
        "inputs_used": [
            {"file_name": p.name, "bytes": p.stat().st_size} for p in input_paths
        ],
        "message": "Reference runner output",
    }

    output_path = work_dir / "result.json"
    output_path.write_text(json.dumps(result, indent=2))
    runner.report_progress(90, "Uploading result")
    return output_path


def main() -> int:
    with Runner.from_env() as runner:
        try:
            job = runner.get_input()
            with tempfile.TemporaryDirectory() as tmp:
                output_path = run_inference(runner, job, Path(tmp))
                runner.upload_artifact(
                    output_path,
                    content_type="application/json",
                    artifact_type="text",
                    preview_supported=True,
                )
            runner.succeed()
            return 0
        except Exception as exc:  # noqa: BLE001 - report any failure to the platform
            runner.fail("RUNNER_ERROR", str(exc))
            print(f"runner failed: {exc}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(main())
