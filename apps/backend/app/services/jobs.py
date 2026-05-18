from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Artifact, Job
from app.schemas.jobs import JobStatus
from app.services.job_transitions import JobTransitionError, ensure_transition
from app.services.storage import save_job_input_file, save_job_output_file
from uuid import UUID


async def create_job_service(
    db: AsyncSession,
    space_id: UUID,
    user_id: UUID,
    input_payload: dict[str, Any],
    files: dict[str, UploadFile],
) -> Job:
    job = Job(
        space_id=space_id,
        user_id=user_id,
        input_payload=dict(input_payload),
        status=JobStatus.QUEUED.value,
    )

    db.add(job)
    await db.flush()

    try:
        input_artifacts: dict[str, str] = {}

        for field_name, upload in files.items():
            storage_path, size_bytes, stored_name = await save_job_input_file(
                job_id=job.id, file=upload
            )
            artifact = Artifact(
                job_id=job.id,
                artifact_type="INPUT",
                file_name=stored_name,
                content_type=upload.content_type or "application/octet-stream",
                size_bytes=size_bytes,
                storage_path=storage_path,
                preview_supported=False,
            )
            db.add(artifact)
            await db.flush()
            input_artifacts[field_name] = str(artifact.id)

        if input_artifacts:
            job.input_payload = {
                **input_payload,
                "input_artifacts": input_artifacts,
            }

        await db.commit()
    except Exception:
        await db.rollback()
        raise

    await db.refresh(job)
    return job


async def get_job_by_id_service(db: AsyncSession, job_id: UUID) -> Job | None:
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def cancel_job_service(db: AsyncSession, job: Job) -> Job:
    ensure_transition(job.status, JobStatus.CANCELLED)
    job.status = JobStatus.CANCELLED.value
    job.cancelled_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return job


async def update_job_progress_service(
    db: AsyncSession,
    job: Job,
    *,
    progress_percent: int,
    message: str | None,
) -> Job:
    now = datetime.now(timezone.utc)

    if job.status == JobStatus.QUEUED.value:
        ensure_transition(job.status, JobStatus.RUNNING)
        job.status = JobStatus.RUNNING.value
        job.started_at = now
    elif job.status != JobStatus.RUNNING.value:
        raise JobTransitionError(
            f"Cannot update progress while job status is {job.status}"
        )

    job.progress_percent = progress_percent
    job.progress_message = message
    await db.commit()
    await db.refresh(job)
    return job


async def succeed_job_service(db: AsyncSession, job: Job) -> Job:
    ensure_transition(job.status, JobStatus.COMPLETED)
    now = datetime.now(timezone.utc)
    job.status = JobStatus.COMPLETED.value
    job.progress_percent = 100
    job.finished_at = now
    if job.started_at is None:
        job.started_at = now
    await db.commit()
    await db.refresh(job)
    return job


async def fail_job_service(
    db: AsyncSession,
    job: Job,
    *,
    error_code: str | None,
    error_message: str,
) -> Job:
    ensure_transition(job.status, JobStatus.FAILED)
    now = datetime.now(timezone.utc)
    job.status = JobStatus.FAILED.value
    job.error_code = error_code
    job.error_message = error_message
    job.finished_at = now
    if job.started_at is None:
        job.started_at = now
    await db.commit()
    await db.refresh(job)
    return job


async def create_output_artifact_service(
    db: AsyncSession,
    job: Job,
    *,
    file: UploadFile,
    artifact_type: str,
    preview_supported: bool,
) -> Artifact:
    storage_path, size_bytes, stored_name = await save_job_output_file(job_id=job.id, file=file)
    expires_at = datetime.now(timezone.utc) + timedelta(days=14)

    artifact = Artifact(
        job_id=job.id,
        artifact_type=artifact_type,
        file_name=stored_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        storage_path=storage_path,
        preview_supported=preview_supported,
        expires_at=expires_at,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return artifact
