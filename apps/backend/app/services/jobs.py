from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import UploadFile, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Artifact, Job
from app.schemas.jobs import JobStatus, JobSubmitResponse
from app.services.job_transitions import JobTransitionError, ensure_transition
from app.services.storage import save_job_input_file, save_job_output_file

JOB_RETENTION_DAYS = 14


async def _count_queued_jobs(db: AsyncSession) -> int:
    """Returns the current number of QUEUED jobs, used to assign the next queue position."""
    result = await db.execute(
        select(func.count()).select_from(Job).where(Job.status == JobStatus.QUEUED.value)
    )
    return int(result.scalar_one())


async def recalculate_queue_positions(db: AsyncSession) -> None:
    """Reassigns contiguous queue positions to all QUEUED jobs (sorted by creation time).
    Called after a job starts or is cancelled so the queue numbers stay sequential."""
    result = await db.execute(
        select(Job)
        .where(Job.status == JobStatus.QUEUED.value)
        .order_by(Job.created_at.asc())
    )
    queued_jobs = list(result.scalars().all())
    for index, job in enumerate(queued_jobs, start=1):
        job.queue_position = index
    await db.commit()


async def create_job_service(
    db: AsyncSession,
    space_id: UUID,
    user_id: UUID,
    input_payload: dict[str, Any],
    files: dict[str, UploadFile],
) -> JobSubmitResponse:
    """Creates a new QUEUED job, saves any uploaded input files as INPUT artifacts,
    and patches input_payload with the artifact IDs so the runner can locate the files.
    The job expires after JOB_RETENTION_DAYS days."""
    now = datetime.now(timezone.utc)
    queue_position = await _count_queued_jobs(db) + 1

    job = Job(
        space_id=space_id,
        user_id=user_id,
        input_payload=dict(input_payload),
        status=JobStatus.QUEUED.value,
        queue_position=queue_position,
        expires_at=now + timedelta(days=JOB_RETENTION_DAYS),
    )

    db.add(job)
    await db.flush()

    try:
        input_artifacts: dict[str, str] = {}

        for field_name, upload in files.items():
            storage_path, size_bytes, stored_name = await save_job_input_file(job_id=job.id, file=upload)
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
            job.input_payload = {**input_payload, "input_artifacts": input_artifacts}

        await db.commit()
    except Exception:
        await db.rollback()
        raise

    await db.refresh(job)
    return JobSubmitResponse(id=job.id, status=JobStatus(job.status), queue_position=job.queue_position)


async def get_job_by_id_service(db: AsyncSession, job_id: UUID) -> Job | None:
    """Looks up a job by its UUID. Returns None if not found."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def list_jobs_by_status_service(db: AsyncSession, status: JobStatus) -> list[Job]:
    """Returns all jobs with the given status, ordered by creation time ascending (oldest first).
    Used by the orchestrator to pick the next QUEUED job."""
    result = await db.execute(
        select(Job).where(Job.status == status.value).order_by(Job.created_at.asc())
    )
    return list(result.scalars().all())


async def list_jobs_by_user_service(db: AsyncSession, user_id: UUID) -> list[Job]:
    """Returns all jobs for a user with the associated space eagerly loaded (for space_name),
    sorted newest first for the history view."""
    result = await db.execute(
        select(Job).options(selectinload(Job.space)).where(Job.user_id == user_id).order_by(Job.created_at.desc())
    )
    return list(result.scalars().all())


async def start_job_service(db: AsyncSession, job: Job) -> Job:
    """Transitions a job from QUEUED to STARTING and recalculates queue positions for
    the remaining queued jobs."""
    ensure_transition(job.status, JobStatus.STARTING)
    job.status = JobStatus.STARTING.value
    job.queue_position = None
    await db.commit()
    await recalculate_queue_positions(db)
    await db.refresh(job)
    return job


async def cancel_job_service(db: AsyncSession, job: Job) -> Job:
    """Cancels a job. QUEUED jobs are cancelled immediately; STARTING/RUNNING jobs transition
    through CANCELLING first. Recalculates queue positions if a queued job was removed.
    Raises JobTransitionError if the current status does not allow cancellation."""
    now = datetime.now(timezone.utc)
    was_queued = job.status == JobStatus.QUEUED.value

    if was_queued:
        ensure_transition(job.status, JobStatus.CANCELLED)
        job.status = JobStatus.CANCELLED.value
        job.queue_position = None
        job.cancelled_at = now
    elif job.status in {JobStatus.STARTING.value, JobStatus.RUNNING.value}:
        ensure_transition(job.status, JobStatus.CANCELLING)
        job.status = JobStatus.CANCELLING.value
        ensure_transition(job.status, JobStatus.CANCELLED)
        job.status = JobStatus.CANCELLED.value
        job.cancelled_at = now
    else:
        raise JobTransitionError(f"Cannot cancel job with status {job.status}")

    await db.commit()
    if was_queued:
        await recalculate_queue_positions(db)
    await db.refresh(job)
    return job


async def update_job_progress_service(
    db: AsyncSession,
    job: Job,
    *,
    progress_percent: int,
    message: str | None,
) -> Job:
    """Updates progress on a running job. Implicitly transitions STARTING -> RUNNING on the first
    progress call (which also sets started_at). Raises JobTransitionError for other statuses."""
    now = datetime.now(timezone.utc)

    if job.status == JobStatus.STARTING.value:
        ensure_transition(job.status, JobStatus.RUNNING)
        job.status = JobStatus.RUNNING.value
        job.started_at = now
    elif job.status != JobStatus.RUNNING.value:
        raise JobTransitionError(f"Cannot update progress while job status is {job.status}")

    job.progress_percent = progress_percent
    job.progress_message = message
    await db.commit()
    await db.refresh(job)
    return job


async def succeed_job_service(db: AsyncSession, job: Job) -> Job:
    """Marks the job as SUCCEEDED and sets finished_at. Sets started_at to now as well
    if the runner skipped the RUNNING state entirely."""
    ensure_transition(job.status, JobStatus.SUCCEEDED)
    now = datetime.now(timezone.utc)
    job.status = JobStatus.SUCCEEDED.value
    job.progress_percent = 100
    job.progress_message = job.progress_message or "Completed"
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
    """Marks the job as FAILED with an error code and message reported by the runner."""
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
    """Saves a runner-produced output file to disk and creates the Artifact record for it.
    The artifact expires at the same time as the job (JOB_RETENTION_DAYS from now)."""
    storage_path, size_bytes, stored_name = await save_job_output_file(job_id=job.id, file=file)
    expires_at = datetime.now(timezone.utc) + timedelta(days=JOB_RETENTION_DAYS)

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

async def delete_job_from_history_service(
    db: AsyncSession,
    job_id: UUID,
    user_id: UUID,
) -> None:
    """Deletes a job and all its artifacts from the database. Raises HTTP 403 if the
    requesting user does not own the job, 404 if the job does not exist."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not allowed to delete this job")

    # Delete associated artifacts
    artifacts_result = await db.execute(select(Artifact).where(Artifact.job_id == job_id))
    artifacts = artifacts_result.scalars().all()
    for artifact in artifacts:
        await db.delete(artifact)

    await db.delete(job)
    await db.commit()
