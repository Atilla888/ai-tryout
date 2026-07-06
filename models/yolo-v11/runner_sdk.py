"""AI-Spaces runner SDK.

A thin client over the platform's internal runner API so a model author only
writes inference code, not queue/progress/artifact plumbing (US-10, spec 5.4).

Typical usage in a runner:

    from runner_sdk import Runner

    with Runner.from_env() as runner:
        job = runner.get_input()
        prompt = job.input_payload.get("prompt", "")
        for path in runner.download_inputs("./inputs"):
            ...  # use the uploaded input files
        runner.report_progress(50, "halfway")
        runner.upload_artifact("out.jpg", "image/jpeg", artifact_type="image",
                               preview_supported=True)
        runner.succeed()

If anything throws, call ``runner.fail(code, message)`` (or wrap your run in
``Runner.run(...)`` which does this for you).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx


@dataclass
class RunnerInputArtifact:
    id: int
    file_name: str
    content_type: str
    size_bytes: int
    content_url: str
    field_name: str | None = None


@dataclass
class RunnerInput:
    job_id: int
    space_id: int
    input_payload: dict[str, Any]
    input_artifacts: list[RunnerInputArtifact] = field(default_factory=list)


class Runner:
    """Client bound to a single job."""

    def __init__(self, *, job_id: str, api_base_url: str, token: str, timeout: float = 30.0) -> None:
        self.job_id = str(job_id)
        self._client = httpx.Client(
            base_url=api_base_url.rstrip("/"),
            headers={"X-Service-Token": token},
            timeout=timeout,
        )

    @classmethod
    def from_env(cls) -> "Runner":
        """Build a runner from the environment the orchestrator injects."""
        def _env(*names: str, default: str | None = None) -> str:
            for name in names:
                value = os.environ.get(name, "").strip()
                if value:
                    return value
            if default is not None:
                return default
            raise RuntimeError(f"Missing required environment variable: {names[0]}")

        return cls(
            job_id=_env("JOB_ID"),
            api_base_url=_env("BACKEND_API_URL", "API_BASE_URL", default="http://localhost:8000"),
            token=_env("RUNNER_TOKEN", "INTERNAL_SERVICE_TOKEN"),
        )

    # --- context manager -----------------------------------------------------

    def __enter__(self) -> "Runner":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # --- contract calls ------------------------------------------------------

    def get_input(self) -> RunnerInput:
        """GET /internal/jobs/{id}/runner-input — payload + uploaded input files."""
        resp = self._client.get(f"/internal/jobs/{self.job_id}/runner-input")
        resp.raise_for_status()
        data = resp.json()
        return RunnerInput(
            job_id=data["job_id"],
            space_id=data["space_id"],
            input_payload=data.get("input_payload", {}),
            input_artifacts=[RunnerInputArtifact(**a) for a in data.get("input_artifacts", [])],
        )

    def download_inputs(self, dest_dir: str | Path) -> list[Path]:
        """Download every uploaded INPUT file into ``dest_dir``; returns the paths."""
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for artifact in self.get_input().input_artifacts:
            resp = self._client.get(artifact.content_url)
            resp.raise_for_status()
            target = dest / artifact.file_name
            target.write_bytes(resp.content)
            paths.append(target)
        return paths

    def report_progress(self, percent: int, message: str | None = None) -> None:
        """PATCH /internal/jobs/{id}/progress — the first call flips the job to RUNNING."""
        self._client.patch(
            f"/internal/jobs/{self.job_id}/progress",
            json={"progress_percent": percent, "message": message},
        ).raise_for_status()

    def is_cancelling(self) -> bool:
        """True once the user has requested cancellation, so the runner can stop early."""
        resp = self._client.get(f"/internal/jobs/{self.job_id}")
        if resp.status_code == 404:
            return True
        resp.raise_for_status()
        return resp.json().get("status") in {"CANCELLING", "CANCELLED"}

    def upload_artifact(
        self,
        file_path: str | Path,
        content_type: str,
        *,
        artifact_type: str,
        preview_supported: bool = False,
    ) -> dict[str, Any]:
        """POST /internal/jobs/{id}/artifacts — register a generated output file."""
        path = Path(file_path)
        with path.open("rb") as handle:
            resp = self._client.post(
                f"/internal/jobs/{self.job_id}/artifacts",
                data={"artifact_type": artifact_type, "preview_supported": str(preview_supported).lower()},
                files={"file": (path.name, handle, content_type)},
            )
        resp.raise_for_status()
        return resp.json()

    def succeed(self) -> None:
        """PATCH /internal/jobs/{id}/succeed — mark the job COMPLETED."""
        self._client.patch(f"/internal/jobs/{self.job_id}/succeed").raise_for_status()

    def fail(self, error_code: str, error_message: str) -> None:
        """PATCH /internal/jobs/{id}/fail — mark the job FAILED."""
        try:
            self._client.patch(
                f"/internal/jobs/{self.job_id}/fail",
                json={"error_code": error_code, "error_message": error_message},
            )
        except httpx.HTTPError:
            pass
