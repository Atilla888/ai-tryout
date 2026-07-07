#!/usr/bin/env python3
"""Poll queued jobs, start them, and run a model runner through a runner backend.

The orchestrator is intentionally thin: it claims queued jobs, asks the backend
for the execution data, and hands off to a runner backend (local subprocess or a
Kubernetes Job — see ``runner_backends.py``). It also drives real cancellation:
when a job is CANCELLING it terminates the worker and finalizes the job to
CANCELLED (D2).
"""

from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from runner_backends import RunnerBackend, build_runner_backend

# CANCELLING is excluded: _handle_cancellations() already terminates those workers
# and calls _finalize_cancel(), so treating them as ACTIVE would race with that path.
ACTIVE_STATUSES = frozenset({"STARTING", "RUNNING"})


def _env_int(name: str, default: int) -> int:
    """Reads an integer environment variable, falling back to a default when unset."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return int(raw)


def _env_str(name: str, default: str | None = None) -> str:
    """Reads a string environment variable, falling back to a default or exiting if it is required and unset."""
    value = os.environ.get(name, "").strip()
    if value:
        return value
    if default is not None:
        return default
    print(f"Missing required environment variable: {name}", file=sys.stderr)
    sys.exit(1)


@dataclass
class RunnerHandle:
    """Pairs a job id with the opaque backend handle for its running worker."""
    job_id: str
    handle: Any


@dataclass
class Orchestrator:
    """Polls the backend for jobs, dispatches runners via a backend, and drives their lifecycle and cancellation."""
    api_base_url: str
    service_token: str
    concurrency_limit: int
    poll_interval_seconds: float
    backend: RunnerBackend
    client: httpx.Client = field(init=False, repr=False)
    active: dict[str, RunnerHandle] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.client = httpx.Client(
            base_url=self.api_base_url.rstrip("/"),
            headers={"X-Service-Token": self.service_token},
            timeout=30.0,
        )

    def close(self) -> None:
        """Closes the underlying HTTP client."""
        self.client.close()

    def _log(self, message: str, *args: object) -> None:
        """Logs a message at INFO level with lazy %-formatting arguments."""
        logging.info(message, *args)

    # --- backend API helpers -------------------------------------------------

    def _fetch_jobs(self, status: str) -> list[dict]:
        """Fetches the list of jobs currently in the given status from the internal API."""
        response = self.client.get("/internal/jobs", params={"status": status})
        response.raise_for_status()
        return response.json()

    def _fetch_execution_data(self, job_id: str) -> dict | None:
        """Fetches a job's execution data, returning None if the job is not found (404)."""
        response = self.client.get(f"/internal/jobs/{job_id}/execution-data")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def _start_job(self, job_id: str) -> bool:
        """Transitions the job to STARTING, returning False if the backend rejects the claim (409)."""
        response = self.client.patch(f"/internal/jobs/{job_id}/start")
        if response.status_code == 409:
            self._log("job=%s start rejected: %s", job_id, response.text)
            return False
        response.raise_for_status()
        self._log("job=%s transitioned to STARTING", job_id)
        return True

    def _get_job_status(self, job_id: str) -> str | None:
        """Returns the job's current status, or None if the job no longer exists (404)."""
        response = self.client.get(f"/internal/jobs/{job_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json().get("status")

    def _fail_job_if_active(self, job_id: str, *, error_code: str, error_message: str) -> None:
        """Marks the job FAILED via the internal API, but only if it is still in an active (STARTING/RUNNING) state."""
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

    def _finalize_cancel(self, job_id: str) -> None:
        """Finalizes a CANCELLING job to CANCELLED, skipping quietly if it is already gone or in a conflicting state (404/409)."""
        response = self.client.patch(f"/internal/jobs/{job_id}/cancelled")
        if response.status_code in (404, 409):
            self._log("job=%s finalize cancel skipped: %s", job_id, response.text)
            return
        response.raise_for_status()
        self._log("job=%s finalized CANCELLED", job_id)

    # --- lifecycle steps -----------------------------------------------------

    def _spawn_runner(self, job_id: str, execution_data: dict) -> Any | None:
        """Starts a runner via the backend, returning its handle, or fails the job and returns None on any spawn error."""
        try:
            return self.backend.start(job_id, execution_data)
        except Exception as exc:  # noqa: BLE001 - report any spawn failure as a job failure
            self._log("job=%s failed to start runner: %s", job_id, exc)
            self._fail_job_if_active(
                job_id,
                error_code="RUNNER_SPAWN_ERROR",
                error_message=str(exc),
            )
            return None

    def _reap_finished(self) -> None:
        """Polls each active runner, failing jobs whose worker exited non-zero without reporting, then drops finished ones from the active set."""
        finished: list[str] = []
        for job_id, runner in self.active.items():
            exit_code = self.backend.poll(runner.handle)
            if exit_code is None:
                continue
            finished.append(job_id)
            self._log("job=%s runner exited code=%s", job_id, exit_code)
            if exit_code != 0:
                # Safety net: the worker died without reporting a terminal status.
                self._fail_job_if_active(
                    job_id,
                    error_code="RUNNER_EXIT_ERROR",
                    error_message=f"Runner process exited with code {exit_code}",
                )
            self.backend.cleanup(runner.handle)

        for job_id in finished:
            del self.active[job_id]

    def _handle_cancellations(self) -> None:
        """Terminate workers for CANCELLING jobs, then finalize them to CANCELLED (D2)."""
        try:
            cancelling = self._fetch_jobs("CANCELLING")
        except httpx.HTTPError as exc:
            self._log("failed to fetch cancelling jobs: %s", exc)
            return

        for job in cancelling:
            job_id = str(job["id"])
            runner = self.active.pop(job_id, None)
            if runner is not None:
                self._log("job=%s cancelling — terminating worker", job_id)
                try:
                    self.backend.terminate(runner.handle)
                    self.backend.cleanup(runner.handle)
                except Exception as exc:  # noqa: BLE001
                    self._log("job=%s error terminating worker: %s", job_id, exc)
            self._finalize_cancel(job_id)

    def _dispatch(self) -> None:
        """Claims and starts at most one QUEUED job per tick, respecting the concurrency limit and skipping jobs without execution data."""
        if len(self.active) >= self.concurrency_limit:
            return

        queued = self._fetch_jobs("QUEUED")
        if not queued:
            return

        # One job per tick deliberately: avoids a burst of parallel spawns on
        # startup and keeps the dispatch loop responsive to cancellations.
        job = queued[0]
        job_id = str(job["id"])
        if job_id in self.active:
            return

        execution_data = self._fetch_execution_data(job_id)
        if execution_data is None:
            self._log("job=%s has no execution data, skipping", job_id)
            return

        if not self._start_job(job_id):
            return

        handle = self._spawn_runner(job_id, execution_data)
        if handle is None:
            return

        self.active[job_id] = RunnerHandle(job_id=job_id, handle=handle)

    def run_forever(self) -> None:
        """Runs the main loop: reap finished runners, handle cancellations, dispatch new jobs, and sleep, terminating all workers on interrupt."""
        self._log(
            "orchestrator started api=%s backend=%s concurrency=%s poll=%ss",
            self.api_base_url,
            self.backend.name,
            self.concurrency_limit,
            self.poll_interval_seconds,
        )
        try:
            while True:
                self._reap_finished()
                self._handle_cancellations()
                self._dispatch()
                time.sleep(self.poll_interval_seconds)
        except KeyboardInterrupt:
            self._log("orchestrator shutting down")
            for runner in self.active.values():
                try:
                    self.backend.terminate(runner.handle)
                except Exception:  # noqa: BLE001
                    pass


def main() -> None:
    """Configures logging, builds the runner backend from the environment, and runs the orchestrator until shutdown."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    api_base_url = _env_str("API_BASE_URL", "http://localhost:8000")
    service_token = _env_str("INTERNAL_SERVICE_TOKEN")
    runner_backend_name = _env_str("RUNNER_BACKEND", "subprocess")

    runner_script: Path | None = None
    if runner_backend_name.lower() == "subprocess":
        runner_script = Path(_env_str("RUNNER_SCRIPT"))
        if not runner_script.is_file():
            print(f"Runner script not found: {runner_script}", file=sys.stderr)
            sys.exit(1)

    backend = build_runner_backend(
        backend=runner_backend_name,
        api_base_url=api_base_url,
        service_token=service_token,
        runner_script=runner_script,
        namespace=_env_str("K8S_NAMESPACE", "default"),
    )

    orchestrator = Orchestrator(
        api_base_url=api_base_url,
        service_token=service_token,
        concurrency_limit=_env_int("CONCURRENCY_LIMIT", 2),
        poll_interval_seconds=float(_env_int("POLL_INTERVAL_SECONDS", 3)),
        backend=backend,
    )
    try:
        orchestrator.run_forever()
    finally:
        orchestrator.close()


if __name__ == "__main__":
    main()
