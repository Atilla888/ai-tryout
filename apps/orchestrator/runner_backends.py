"""Pluggable runner backends for the orchestrator.

The orchestrator decides *which* job to run; a runner backend decides *how* the
worker is started, polled, and stopped. Two backends exist:

* :class:`SubprocessRunnerBackend` runs a local Python runner script as a child
  process. It needs no cluster and is used for local development and tests.
* :class:`KubernetesRunnerBackend` launches one Kubernetes Job per platform job
  from the space's container image (spec 5.6, F2). The ``kubernetes`` client is
  imported lazily so the subprocess path has no hard dependency on it.

Both expose the same small interface so ``main.py`` stays backend-agnostic:

    handle = backend.start(job_id, execution_data)
    code = backend.poll(handle)      # None while running, int exit code when done
    backend.terminate(handle)        # stop a running worker (cancellation)
    backend.cleanup(handle)          # remove a finished workload
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# How long to wait for a worker to exit gracefully before force-killing it.
GRACEFUL_TERMINATION_SECONDS = 10


def _runner_env(job_id: str, execution_data: dict[str, Any], api_base_url: str, service_token: str) -> dict[str, str]:
    """The environment contract every runner receives (spec 5.6)."""
    space_id = execution_data.get("space_id")
    input_reference = execution_data.get("input_reference", job_id)
    return {
        "JOB_ID": str(job_id),
        "SPACE_ID": str(space_id) if space_id is not None else "",
        "BACKEND_API_URL": api_base_url,
        # Both names are injected so old runners (which read API_BASE_URL) and new
        # runners (which read BACKEND_API_URL) both work without a coordinated rename.
        "API_BASE_URL": api_base_url,
        "RUNNER_TOKEN": service_token,
        "INTERNAL_SERVICE_TOKEN": service_token,
        "INPUT_REFERENCE": str(input_reference),
    }


class RunnerBackend(ABC):
    name: str = "runner"

    @abstractmethod
    def start(self, job_id: str, execution_data: dict[str, Any]) -> Any:
        """Launch a worker for the job and return an opaque handle."""

    @abstractmethod
    def poll(self, handle: Any) -> int | None:
        """Return the exit code if the worker finished, otherwise None."""

    @abstractmethod
    def terminate(self, handle: Any) -> None:
        """Stop a running worker (used for cancellation)."""

    def cleanup(self, handle: Any) -> None:
        """Remove a finished workload. No-op by default."""


class SubprocessRunnerBackend(RunnerBackend):
    """Run the runner as a local child process (no cluster required)."""

    name = "subprocess"

    def __init__(self, runner_script: Path, api_base_url: str, service_token: str) -> None:
        self.runner_script = runner_script
        self.api_base_url = api_base_url
        self.service_token = service_token

    def start(self, job_id: str, execution_data: dict[str, Any]) -> subprocess.Popen[bytes]:
        env = os.environ.copy()
        env.update(_runner_env(job_id, execution_data, self.api_base_url, self.service_token))
        process = subprocess.Popen(
            [sys.executable, str(self.runner_script)],
            env=env,
            cwd=self.runner_script.parent,
        )
        logger.info("job=%s spawned runner pid=%s", job_id, process.pid)
        return process

    def poll(self, handle: subprocess.Popen[bytes]) -> int | None:
        return handle.poll()

    def terminate(self, handle: subprocess.Popen[bytes]) -> None:
        if handle.poll() is not None:
            return
        handle.terminate()
        try:
            handle.wait(timeout=GRACEFUL_TERMINATION_SECONDS)
        except subprocess.TimeoutExpired:
            handle.kill()
            handle.wait()


class KubernetesRunnerBackend(RunnerBackend):
    """Launch one Kubernetes Job per platform job from the space's image (F2)."""

    name = "kubernetes"

    def __init__(
        self,
        api_base_url: str,
        service_token: str,
        namespace: str,
        *,
        job_name_prefix: str = "aispaces-job",
        backoff_limit: int = 0,
        active_deadline_seconds: int | None = None,
    ) -> None:
        # Imported here so the subprocess backend never needs the kubernetes client.
        from kubernetes import client, config

        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()

        self._client = client
        self._batch = client.BatchV1Api()
        self.api_base_url = api_base_url
        self.service_token = service_token
        self.namespace = namespace
        self.job_name_prefix = job_name_prefix
        self.backoff_limit = backoff_limit
        self.active_deadline_seconds = active_deadline_seconds

    def _job_name(self, job_id: str) -> str:
        return f"{self.job_name_prefix}-{job_id}"

    def start(self, job_id: str, execution_data: dict[str, Any]) -> str:
        runner_image = execution_data.get("runner_image")
        if not runner_image:
            raise ValueError(f"job={job_id} has no runner image in execution data")

        runner_config = execution_data.get("runner_config") or {}

        # Base contract env, plus any space-defined extras (e.g. model variant,
        # output format) from runner_config.env.
        env = _runner_env(job_id, execution_data, self.api_base_url, self.service_token)
        for key, value in (runner_config.get("env") or {}).items():
            env[str(key)] = str(value)
        env_vars = [self._client.V1EnvVar(name=key, value=value) for key, value in env.items()]

        # GPU request: models like ACE-Step need a GPU scheduled onto the pod.
        # Without this every runner lands on a CPU node (spec F2).
        resources = None
        gpu = runner_config.get("gpu")
        if isinstance(gpu, int) and not isinstance(gpu, bool) and gpu > 0:
            resources = self._client.V1ResourceRequirements(limits={"nvidia.com/gpu": str(gpu)})

        # Optional model-weights volume so multi-GB weights are mounted (e.g. from
        # an NFS-backed PVC shared across runners) instead of baked into the image.
        volumes = None
        volume_mounts = None
        weights_pvc = runner_config.get("weights_pvc")
        if weights_pvc:
            mount_path = str(runner_config.get("weights_mount") or "/models")
            volume_mounts = [self._client.V1VolumeMount(name="model-weights", mount_path=mount_path)]
            volumes = [
                self._client.V1Volume(
                    name="model-weights",
                    persistent_volume_claim=self._client.V1PersistentVolumeClaimVolumeSource(
                        claim_name=str(weights_pvc)
                    ),
                )
            ]

        container = self._client.V1Container(
            name="runner",
            image=runner_image,
            env=env_vars,
            resources=resources,
            volume_mounts=volume_mounts,
        )
        # restart_policy="Never" ensures each pod runs exactly once. Combined with
        # backoff_limit=0 this means K8s will not restart or retry the container.
        pod_spec = self._client.V1PodSpec(
            restart_policy="Never",
            containers=[container],
            volumes=volumes,
        )
        template = self._client.V1PodTemplateSpec(
            metadata=self._client.V1ObjectMeta(labels={"app": "ai-spaces-runner", "job-id": str(job_id)}),
            spec=pod_spec,
        )
        job_spec = self._client.V1JobSpec(
            template=template,
            # backoff_limit=0 disables K8s-level retries. The backend owns the
            # failure/retry logic; if K8s retried, the backend could receive a
            # second succeed/fail notification for the same job.
            backoff_limit=self.backoff_limit,
            active_deadline_seconds=self.active_deadline_seconds,
            # Auto-delete finished Jobs after 1 h so the cluster doesn't accumulate
            # stale Job objects. cleanup() handles early deletion on cancellation.
            ttl_seconds_after_finished=3600,
        )
        job = self._client.V1Job(
            metadata=self._client.V1ObjectMeta(name=self._job_name(job_id)),
            spec=job_spec,
        )
        self._batch.create_namespaced_job(namespace=self.namespace, body=job)
        logger.info("job=%s created k8s Job %s image=%s", job_id, self._job_name(job_id), runner_image)
        return self._job_name(job_id)

    def poll(self, handle: str) -> int | None:
        from kubernetes.client.rest import ApiException

        try:
            job = self._batch.read_namespaced_job_status(name=handle, namespace=self.namespace)
        except ApiException as exc:
            if exc.status == 404:
                return 0  # already gone; treat as finished
            raise
        status = job.status
        if status.succeeded:
            return 0
        if status.failed:
            return 1
        return None

    def terminate(self, handle: str) -> None:
        self.cleanup(handle)

    def cleanup(self, handle: str) -> None:
        from kubernetes.client.rest import ApiException

        try:
            self._batch.delete_namespaced_job(
                name=handle,
                namespace=self.namespace,
                propagation_policy="Background",
            )
            logger.info("deleted k8s Job %s", handle)
        except ApiException as exc:
            if exc.status != 404:
                logger.warning("failed to delete k8s Job %s: %s", handle, exc)


def build_runner_backend(
    *,
    backend: str,
    api_base_url: str,
    service_token: str,
    runner_script: Path | None,
    namespace: str,
) -> RunnerBackend:
    """Construct the configured runner backend."""
    backend = backend.lower()
    if backend == "kubernetes":
        return KubernetesRunnerBackend(
            api_base_url=api_base_url,
            service_token=service_token,
            namespace=namespace,
        )
    if backend == "subprocess":
        if runner_script is None:
            raise ValueError("RUNNER_SCRIPT is required for the subprocess backend")
        return SubprocessRunnerBackend(
            runner_script=runner_script,
            api_base_url=api_base_url,
            service_token=service_token,
        )
    raise ValueError(f"Unknown RUNNER_BACKEND: {backend!r} (expected 'subprocess' or 'kubernetes')")
