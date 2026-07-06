#!/usr/bin/env python3
"""YOLOv11 object-detection runner for AI-Spaces.

Follows the runner contract: reads the uploaded image, runs detection, uploads
the annotated image as an artifact, and reports progress/status via the SDK.
Weights are baked into the image (see Dockerfile) so the pod needs no internet.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from ultralytics import YOLO

from runner_sdk import Runner


def main() -> int:
    with Runner.from_env() as runner:
        try:
            runner.report_progress(5, "Loading model")
            model = YOLO("yolo11n.pt")

            runner.report_progress(20, "Fetching input image")
            with tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                inputs = runner.download_inputs(work / "inputs")
                if not inputs:
                    runner.fail("NO_INPUT", "No image was uploaded")
                    return 1
                image_path = inputs[0]

                runner.report_progress(50, "Running detection")
                results = model(str(image_path))

                out = work / "result.jpg"
                results[0].save(filename=str(out))

                runner.report_progress(90, "Uploading result")
                runner.upload_artifact(
                    out,
                    "image/jpeg",
                    artifact_type="image",
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