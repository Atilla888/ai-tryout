"""Internal endpoints consumed by the orchestrator and model runners.

These routes must never be exposed publicly — guard with network policy
or a shared secret header (X-Internal-Token) in production.
"""

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Form, HTTPException, UploadFile
from sqlalchemy import select

from app.core.config import settings
from app.dependencies import DbSession
from app.models import Artifact, ArtifactType, Job
from app.schemas import ArtifactRead, JobFailUpdate, JobProgressUpdate, JobRead

router = APIRouter(prefix="/internal", tags=["internal"])

_ARTIFACT_TTL_DAYS = 14


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
    db: DbSession,
    artifact_type: ArtifactType = Form(...),
    preview_supported: bool = Form(False),
) -> ArtifactRead:
    """Model runner uploads a generated output file."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    artifact_id = uuid.uuid4()
    storage_dir = Path(settings.storage_path) / str(job_id)
    storage_dir.mkdir(parents=True, exist_ok=True)

    original_name = file.filename or "upload"
    storage_path = storage_dir / f"{artifact_id}_{original_name}"

    content = await file.read()
    async with aiofiles.open(storage_path, "wb") as f:
        await f.write(content)

    artifact = Artifact(
        id=artifact_id,
        job_id=job_id,
        user_id=job.user_id,
        artifact_type=artifact_type,
        file_name=original_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        storage_path=str(storage_path),
        preview_supported=preview_supported,
        expires_at=datetime.now(timezone.utc) + timedelta(days=_ARTIFACT_TTL_DAYS),
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return artifact  # type: ignore[return-value]


@router.post("/jobs/{job_id}/heartbeat", status_code=204)
async def heartbeat(job_id: uuid.UUID, db: DbSession) -> None:
    """Model runner signals it is still alive during long-running execution."""
    # TODO(Sprint 2): update last_heartbeat_at timestamp
    raise HTTPException(status_code=404, detail="Job not found")
