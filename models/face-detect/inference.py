#!/usr/bin/env python3
"""OpenCV Haar-cascade face-detection runner for AI-Spaces.

Same contract as the YOLO runner (image in -> annotated image out) but with no
PyTorch: it uses the frontal-face Haar cascade that ships inside OpenCV, so
there are no model weights to download and the image stays small.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import cv2

from runner_sdk import Runner

CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"


def main() -> int:
    with Runner.from_env() as runner:
        try:
            runner.report_progress(10, "Loading detector")
            detector = cv2.CascadeClassifier(CASCADE_PATH)

            runner.report_progress(30, "Fetching input image")
            with tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                inputs = runner.download_inputs(work / "inputs")
                if not inputs:
                    runner.fail("NO_INPUT", "No image was uploaded")
                    return 1

                image = cv2.imread(str(inputs[0]))
                if image is None:
                    runner.fail("BAD_INPUT", "Uploaded file is not a readable image")
                    return 1

                runner.report_progress(60, "Detecting faces")
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                faces = detector.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                )
                for (x, y, w, h) in faces:
                    cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)

                out = work / "result.jpg"
                cv2.imwrite(str(out), image)

                runner.report_progress(90, f"Uploading result ({len(faces)} face(s))")
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