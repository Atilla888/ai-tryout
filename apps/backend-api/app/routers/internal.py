"""Internal endpoints consumed by the orchestrator and model runners.

These routes must never be exposed publicly — guard with network policy
or a shared secret header (X-Internal-Token) in production.
"""

import uuid

from fastapi import APIRouter, HTTPException, UploadFile

from app.dependencies import DbSession
from app.schemas import ArtifactRead, JobFailUpdate, JobProgressUpdate, JobRead

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/jobs/{job_id}/runner-input")
async def get_runner_input(job_id: uuid.UUID, db: DbSession) -> dict:
    """Return validated input payload and upload references for the runner."""
    # TODO(S1-06): fetch job input_payload, raise 404 if not found
    raise HTTPException(status_code=404, detail="Job not found")


@router.patch("/jobs/{job_id}/progress", response_model=JobRead)
async def update_progress(
    job_id: uuid.UUID, body: JobProgressUpdate, db: DbSession
) -> JobRead:
    """Model runner reports current progress percentage and message."""
    # TODO(S1-06): update job.progress_percent + progress_message
    raise HTTPException(status_code=404, detail="Job not found")


@router.patch("/jobs/{job_id}/succeed", response_model=JobRead)
async def succeed_job(job_id: uuid.UUID, db: DbSession) -> JobRead:
    """Model runner reports successful completion."""
    # TODO(S1-06): transition RUNNING → COMPLETED
    raise HTTPException(status_code=404, detail="Job not found")


@router.patch("/jobs/{job_id}/fail", response_model=JobRead)
async def fail_job(job_id: uuid.UUID, body: JobFailUpdate, db: DbSession) -> JobRead:
    """Model runner reports failure with error code and message."""
    # TODO(S1-06): transition RUNNING → FAILED, store error details
    raise HTTPException(status_code=404, detail="Job not found")


@router.post("/jobs/{job_id}/artifacts", response_model=ArtifactRead, status_code=201)
async def upload_artifact(
    job_id: uuid.UUID,
    file: UploadFile,
    artifact_type: str,
    preview_supported: bool = False,
    db: DbSession = None,  # type: ignore[assignment]
) -> ArtifactRead:
    """Model runner uploads a generated output file."""
    # TODO(S1-07): store file to STORAGE_PATH, create artifact record
    raise HTTPException(status_code=404, detail="Job not found")


@router.post("/jobs/{job_id}/heartbeat", status_code=204)
async def heartbeat(job_id: uuid.UUID, db: DbSession) -> None:
    """Model runner signals it is still alive during long-running execution."""
    # TODO(Sprint 2): update last_heartbeat_at timestamp
    raise HTTPException(status_code=404, detail="Job not found")
