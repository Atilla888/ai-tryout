#!/usr/bin/env python3
"""Poll queued jobs, start them, and spawn the fake model runner subprocess."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNNER_SCRIPT = REPO_ROOT / "apps" / "fake-runner" / "fake_runner.py"

ACTIVE_STATUSES = frozenset({"STARTING", "RUNNING"})


def _env_int(name: str, default: int) -> int:
    """Reads an integer from an environment variable, falling back to default if unset."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return int(raw)


def _env_str(name: str, default: str | None = None) -> str:
    """Reads a required string from an environment variable. Exits the process if the
    variable is missing and no default is provided."""
    value = os.environ.get(name, "").strip()
    if value:
        return value
    if default is not None:
        return default
    print(f"Missing required environment variable: {name}", file=sys.stderr)
    sys.exit(1)


@dataclass
class RunnerHandle:
    """Tracks an active runner subprocess alongside its job ID so the orchestrator
    can poll its exit code and fail the job if it crashes."""
    job_id: str
    process: subprocess.Popen[bytes]


@dataclass
class Orchestrator:
    """Polls for QUEUED jobs, dispatches them to runner subprocesses, and handles
    their lifecycle. concurrency_limit caps how many runners run in parallel."""
    api_base_url: str
    service_token: str
    concurrency_limit: int
    poll_interval_seconds: float
    runner_script: Path
    client: httpx.Client = field(init=False, repr=False)
    active: dict[str, RunnerHandle] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.client = httpx.Client(
            base_url=self.api_base_url.rstrip("/"),
            headers={"X-Service-Token": self.service_token},
            timeout=30.0,
        )

    def close(self) -> None:
        self.client.close()

    def _log(self, message: str, *args: object) -> None:
        logging.info(message, *args)

    def _fetch_queued_jobs(self) -> list[dict]:
        """Retrieves all QUEUED jobs from the API, ordered oldest-first."""
        response = self.client.get("/jobs", params={"status": "QUEUED"})
        response.raise_for_status()
        return response.json()

    def _start_job(self, job_id: str) -> bool:
        """Tells the API to transition the job to STARTING. Returns False if the API
        rejects the transition (e.g. another orchestrator already claimed the job)."""
        response = self.client.patch(f"/internal/jobs/{job_id}/start")
        if response.status_code == 409:
            self._log("job=%s start rejected: %s", job_id, response.text)
            return False
        response.raise_for_status()
        self._log("job=%s transitioned to STARTING", job_id)
        return True

    def _spawn_runner(self, job_id: str) -> subprocess.Popen[bytes] | None:
        """Launches the runner script as a subprocess, injecting JOB_ID and auth credentials
        via environment variables. Returns None and fails the job if the process cannot start."""
        env = os.environ.copy()
        env.update(
            {
                "JOB_ID": job_id,
                "API_BASE_URL": self.api_base_url,
                "INTERNAL_SERVICE_TOKEN": self.service_token,
            }
        )
        try:
            process = subprocess.Popen(
                [sys.executable, str(self.runner_script)],
                env=env,
                cwd=self.runner_script.parent,
            )
        except OSError as exc:
            self._log("job=%s failed to spawn runner: %s", job_id, exc)
            self._fail_job_if_active(
                job_id,
                error_code="RUNNER_SPAWN_ERROR",
                error_message=str(exc),
            )
            return None

        self._log("job=%s spawned runner pid=%s", job_id, process.pid)
        return process

    def _get_job_status(self, job_id: str) -> str | None:
        response = self.client.get(f"/jobs/{job_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json().get("status")

    def _fail_job_if_active(self, job_id: str, *, error_code: str, error_message: str) -> None:
        """Marks the job as FAILED only if it is still in an active state. The status check
        avoids sending a fail request when the runner already reported success or failure."""
        status = self._get_job_status(job_id)
        if status not in ACTIVE_STATUSES:
            self._log("job=%s skip fail (status=%s)", job_id, status)
            return
        response = self.client.patch(
            f"/internal/jobs/{job_id}/fail",
            json={"error_code": error_code, "error_message": error_message},
        )
        if response.status_code == 409:
            self._log("job=%s fail rejected: %s", job_id, response.text)
            return
        response.raise_for_status()
        self._log("job=%s marked FAILED (%s)", job_id, error_code)

    def _reap_finished(self) -> None:
        """Checks all active runner processes for completion. If a process has exited with
        a non-zero code, the corresponding job is marked FAILED."""
        finished: list[str] = []
        for job_id, handle in self.active.items():
            exit_code = handle.process.poll()
            if exit_code is None:
                continue
            finished.append(job_id)
            self._log("job=%s runner exited code=%s", job_id, exit_code)
            if exit_code != 0:
                self._fail_job_if_active(
                    job_id,
                    error_code="RUNNER_EXIT_ERROR",
                    error_message=f"Runner process exited with code {exit_code}",
                )

        for job_id in finished:
            del self.active[job_id]

    def _dispatch(self) -> None:
        """Picks the oldest queued job and starts a runner for it if the concurrency limit
        has not been reached. Starts at most one job per poll cycle."""
        if len(self.active) >= self.concurrency_limit:
            return

        queued = self._fetch_queued_jobs()
        if not queued:
            return

        job = queued[0]
        job_id = str(job["id"])
        if job_id in self.active:
            return

        if not self._start_job(job_id):
            return

        process = self._spawn_runner(job_id)
        if process is None:
            return

        self.active[job_id] = RunnerHandle(job_id=job_id, process=process)

    def run_forever(self) -> None:
        """Main poll loop: reaps finished runners, then dispatches new ones, then sleeps.
        Terminates all active runners on KeyboardInterrupt for a clean shutdown."""
        self._log(
            "orchestrator started api=%s concurrency=%s poll=%ss runner=%s",
            self.api_base_url,
            self.concurrency_limit,
            self.poll_interval_seconds,
            self.runner_script,
        )
        try:
            while True:
                self._reap_finished()
                self._dispatch()
                time.sleep(self.poll_interval_seconds)
        except KeyboardInterrupt:
            self._log("orchestrator shutting down")
            for handle in self.active.values():
                if handle.process.poll() is None:
                    handle.process.terminate()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    runner_script = Path(os.environ.get("RUNNER_SCRIPT", str(DEFAULT_RUNNER_SCRIPT)))
    if not runner_script.is_file():
        print(f"Runner script not found: {runner_script}", file=sys.stderr)
        sys.exit(1)

    orchestrator = Orchestrator(
        api_base_url=_env_str("API_BASE_URL", "http://localhost:8000"),
        service_token=_env_str("INTERNAL_SERVICE_TOKEN"),
        concurrency_limit=_env_int("CONCURRENCY_LIMIT", 2),
        poll_interval_seconds=float(_env_int("POLL_INTERVAL_SECONDS", 3)),
        runner_script=runner_script,
    )
    try:
        orchestrator.run_forever()
    finally:
        orchestrator.close()


if __name__ == "__main__":
    main()
