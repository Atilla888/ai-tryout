#!/usr/bin/env python3
"""SAM 3D Objects runner for AI-Spaces.

Receives a single image upload, runs Meta's SAM 3D Objects model to produce a
3-D mesh, and uploads the result as a GLB artifact.

Dev mode (no GPU / no model checkpoints):
    Set DEV_MODE=1 or leave CHECKPOINT_DIR unset. The runner generates a
    placeholder colored cube GLB so the full platform pipeline can be exercised
    without a GPU.

Production mode:
    Expects CHECKPOINT_DIR=/checkpoints/hf (model weights from
    facebook/sam-3d-objects on Hugging Face) and a CUDA-capable GPU.

Environment injected by the orchestrator:
    JOB_ID, SPACE_ID, BACKEND_API_URL, RUNNER_TOKEN, INPUT_REFERENCE
"""
from __future__ import annotations

import json
import logging
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from runner_sdk import Runner, RunnerInput

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

CHECKPOINT_DIR = Path(os.environ.get("CHECKPOINT_DIR", "/checkpoints/hf"))
DEV_MODE = os.environ.get("DEV_MODE", "").lower() in {"1", "true", "yes"} or not CHECKPOINT_DIR.exists()


# ---------------------------------------------------------------------------
# Dev-mode fallback: pure-Python GLB cube (no GPU, no model)
# ---------------------------------------------------------------------------

def _create_demo_glb(output_path: Path) -> None:
    """Write a minimal valid GLB file containing a blue cube.

    This lets the full platform pipeline (submit → progress → artifact → succeed)
    run locally without a GPU or model weights.
    """
    # 8 unique cube vertices (x, y, z) scaled to -1..1
    verts: list[tuple[float, float, float]] = [
        (-1.0, -1.0, -1.0), ( 1.0, -1.0, -1.0),
        ( 1.0,  1.0, -1.0), (-1.0,  1.0, -1.0),
        (-1.0, -1.0,  1.0), ( 1.0, -1.0,  1.0),
        ( 1.0,  1.0,  1.0), (-1.0,  1.0,  1.0),
    ]
    # 12 triangles (2 per face × 6 faces), CCW winding
    indices: list[int] = [
        0, 1, 2,  0, 2, 3,   # front  (z = -1)
        5, 4, 7,  5, 7, 6,   # back   (z = +1)
        4, 0, 3,  4, 3, 7,   # left   (x = -1)
        1, 5, 6,  1, 6, 2,   # right  (x = +1)
        4, 5, 1,  4, 1, 0,   # bottom (y = -1)
        3, 2, 6,  3, 6, 7,   # top    (y = +1)
    ]

    pos_bytes = b"".join(struct.pack("<fff", *v) for v in verts)
    idx_bytes = struct.pack(f"<{len(indices)}H", *indices)
    # Binary chunk must be 4-byte aligned
    idx_bytes += b"\x00" * ((4 - len(idx_bytes) % 4) % 4)
    binary = pos_bytes + idx_bytes

    gltf = {
        "asset": {"version": "2.0", "generator": "AI-Spaces SAM-3D demo"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "DemoCube"}],
        "meshes": [{
            "name": "Cube",
            "primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "material": 0}],
        }],
        "materials": [{
            "name": "Blue",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.18, 0.48, 0.9, 1.0],
                "metallicFactor": 0.1,
                "roughnessFactor": 0.6,
            },
            "doubleSided": True,
        }],
        "accessors": [
            {
                "bufferView": 0, "componentType": 5126,  # FLOAT
                "count": len(verts), "type": "VEC3",
                "min": [-1.0, -1.0, -1.0], "max": [1.0, 1.0, 1.0],
            },
            {
                "bufferView": 1, "componentType": 5123,  # UNSIGNED_SHORT
                "count": len(indices), "type": "SCALAR",
            },
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0,              "byteLength": len(pos_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": len(pos_bytes), "byteLength": len(indices) * 2, "target": 34963},
        ],
        "buffers": [{"byteLength": len(binary)}],
    }

    json_bytes = json.dumps(gltf, separators=(",", ":")).encode()
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)

    total = 12 + 8 + len(json_bytes) + 8 + len(binary)
    header    = struct.pack("<III", 0x46546C67, 2, total)
    json_chunk = struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes
    bin_chunk  = struct.pack("<II", len(binary),     0x004E4942) + binary

    output_path.write_bytes(header + json_chunk + bin_chunk)


# ---------------------------------------------------------------------------
# Production: SAM 3D Objects inference
# ---------------------------------------------------------------------------

def _run_sam3d(image_path: Path, work_dir: Path) -> Path:
    """Run SAM 3D Objects on *image_path* and return a .glb output file.

    Prerequisites (production only):
    - Model weights at CHECKPOINT_DIR (facebook/sam-3d-objects on Hugging Face)
    - CUDA GPU with ≥8 GB VRAM
    - Conda environment 'sam3d-objects' created by the repo's setup script

    The runner calls the model's CLI so it runs in its own conda environment
    without polluting the platform's Python environment.
    """
    output_dir = work_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    repo_dir = Path(os.environ.get("SAM3D_REPO", "/opt/sam-3d-objects"))
    conda_python = Path(os.environ.get(
        "SAM3D_PYTHON",
        "/opt/conda/envs/sam3d-objects/bin/python",
    ))

    cmd = [
        str(conda_python),
        str(repo_dir / "run_demo.py"),
        "--image",      str(image_path),
        "--checkpoint", str(CHECKPOINT_DIR),
        "--output",     str(output_dir),
        "--export-glb",
    ]

    log.info("running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        log.error("sam3d stderr:\n%s", result.stderr)
        raise RuntimeError(f"SAM 3D Objects failed (exit {result.returncode}): {result.stderr[-500:]}")

    glb_files = sorted(output_dir.glob("*.glb"))
    if not glb_files:
        raise RuntimeError("SAM 3D Objects produced no .glb output")

    return glb_files[0]


# ---------------------------------------------------------------------------
# Runner entry point
# ---------------------------------------------------------------------------

def run(runner: Runner, job: RunnerInput, work_dir: Path) -> Path:
    runner.report_progress(5, "Fetching input image")

    # Download the uploaded image
    input_dir = work_dir / "input"
    input_dir.mkdir()
    inputs = runner.download_inputs(input_dir)

    image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    image_path = next(
        (p for p in inputs if p.suffix.lower() in image_extensions),
        inputs[0] if inputs else None,
    )

    if image_path is None:
        raise ValueError("No input image found in job payload")

    output_glb = work_dir / "output.glb"

    if DEV_MODE:
        log.info("DEV_MODE active — generating placeholder cube GLB (no GPU)")
        runner.report_progress(30, "Dev mode: generating placeholder 3D model")
        _create_demo_glb(output_glb)
        runner.report_progress(80, "Dev mode: placeholder ready")
    else:
        runner.report_progress(15, "Loading SAM 3D Objects model")
        runner.report_progress(30, "Running segmentation")
        runner.report_progress(60, "Reconstructing 3D mesh")
        result = _run_sam3d(image_path, work_dir)
        result.rename(output_glb)
        runner.report_progress(85, "Exporting GLB")

    return output_glb


def main() -> int:
    with Runner.from_env() as runner:
        try:
            job = runner.get_input()
            with tempfile.TemporaryDirectory() as tmp:
                output_glb = run(runner, job, Path(tmp))
                runner.report_progress(90, "Uploading 3D model")
                runner.upload_artifact(
                    output_glb,
                    content_type="model/gltf-binary",
                    artifact_type="3d",
                    preview_supported=True,
                )
            runner.succeed()
            return 0
        except Exception as exc:  # noqa: BLE001
            runner.fail("RUNNER_ERROR", str(exc))
            log.error("runner failed: %s", exc)
            return 1


if __name__ == "__main__":
    sys.exit(main())
