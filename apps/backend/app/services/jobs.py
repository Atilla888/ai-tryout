"""Business logic and DB operations for the job lifecycle, queue, and output artifacts."""

from datetime import datetime, timedelta, timezone

from fastapi import UploadFile, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Artifact, Job
from app.schemas.jobs import JobStatus
from app.services.job_transitions import JobTransitionError, ensure_transition
from app.services.serializers import job_to_submit_response
from app.services.storage import (
    delete_job_storage,
    delete_storage_file,
    save_job_input_file,
    save_job_output_file,
)
from uuid import UUID

JOB_RETENTION_DAYS = 14


async def _count_queued_jobs(db: AsyncSession) -> int:
    """How many jobs are waiting right now."""
    result = await db.execute(
        select(func.count()).select_from(Job).where(Job.status == JobStatus.QUEUED.value)
    )
    return int(result.scalar_one())


async def recalculate_queue_positions(db: AsyncSession) -> None:
    """Renumber the queue after something starts or gets cancelled."""
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
    space_id: int,
    user_id: int,
    input_payload: dict,
    files: dict[str, UploadFile],
):
    """Create a queued job, save any uploads, and wire input file ids into the payload."""
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
    # flush (not commit) assigns job.id from the DB sequence so we can use it in
    # the storage path below, while keeping everything in the same transaction.
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
            # Inject artifact UUIDs into the payload so the runner can look up
            # each uploaded file via GET /internal/artifacts/{id}/content without
            # needing to know the raw storage path.
            job.input_payload = {**input_payload, "input_artifacts": input_artifacts}

        await db.commit()
    except Exception:
        await db.rollback()
        raise

    await db.refresh(job)
    return job_to_submit_response(job)


async def get_job_by_public_id_service(db: AsyncSession, public_id: UUID) -> Job | None:
    """Public API lookup by UUID."""
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.space), selectinload(Job.user))
        .where(Job.public_id == public_id)
    )
    return result.scalar_one_or_none()


async def get_job_by_id_service(db: AsyncSession, job_id: int) -> Job | None:
    """Internal lookup by database id (orchestrator and runners use this)."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def get_job_with_space_by_id_service(db: AsyncSession, job_id: int) -> Job | None:
    """Internal lookup that also eager-loads the space (for execution data)."""
    result = await db.execute(
        select(Job).options(selectinload(Job.space)).where(Job.id == job_id)
    )
    return result.scalar_one_or_none()


async def list_jobs_by_status_service(db: AsyncSession, status: JobStatus) -> list[Job]:
    """Oldest first — the orchestrator picks from the front of this list."""
    result = await db.execute(
        select(Job).where(Job.status == status.value).order_by(Job.created_at.asc())
    )
    return list(result.scalars().all())


async def list_jobs_by_user_service(db: AsyncSession, user_id: int) -> list[Job]:
    """A single user's job history, newest first.

    Eager-loads space and user so the rows can be serialized for /me/history
    without extra queries.
    """
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.space), selectinload(Job.user))
        .where(Job.user_id == user_id)
        .order_by(Job.created_at.desc())
    )
    return list(result.scalars().all())


async def start_job_service(db: AsyncSession, job: Job) -> Job:
    """Move a job QUEUED -> STARTING when the orchestrator picks it up.

    Clears the job's queue_position and renumbers the remaining queue so the
    positions stay contiguous (1, 2, 3, ...).
    """
    ensure_transition(job.status, JobStatus.STARTING)
    job.status = JobStatus.STARTING.value
    job.queue_position = None
    await db.commit()
    await recalculate_queue_positions(db)
    await db.refresh(job)
    return job


async def cancel_job_service(db: AsyncSession, job: Job) -> Job:
    """Request cancellation of a job.

    A queued job has no worker yet, so it cancels immediately (QUEUED -> CANCELLED).
    A job that is already executing (STARTING/RUNNING) only moves to CANCELLING here:
    the orchestrator must actually terminate the worker before the job becomes
    CANCELLED (D2). The orchestrator calls :func:`finalize_cancellation_service`
    once the worker is gone.
    """
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
        # Record when the user asked to cancel; finalize sets finished_at later.
        job.cancelled_at = now
    else:
        raise JobTransitionError(f"Cannot cancel job with status {job.status}")

    await db.commit()
    if was_queued:
        await recalculate_queue_positions(db)
    await db.refresh(job)
    return job


async def finalize_cancellation_service(db: AsyncSession, job: Job) -> Job:
    """Move a CANCELLING job to CANCELLED once its worker has been stopped (D2)."""
    ensure_transition(job.status, JobStatus.CANCELLED)
    now = datetime.now(timezone.utc)
    job.status = JobStatus.CANCELLED.value
    job.finished_at = now
    if job.cancelled_at is None:
        job.cancelled_at = now
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
    """First progress update also moves STARTING to RUNNING."""
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
    """Mark a running job SUCCEEDED (terminal).

    Forces progress to 100% and stamps finished_at; backfills started_at if the
    job somehow never reported a start.
    """
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
    """Mark a running job FAILED (terminal) and record why.

    Stores error_code/error_message and stamps finished_at; backfills started_at
    if the job never reported a start.
    """
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
    """Runner finished a file — save it and record the artifact row."""
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
    public_id: UUID,
    user_id: int,
) -> None:
    """Remove a job from the user's history. Only the owner can do this.

    Also removes the job's artifact files and storage directory from disk right
    away, instead of waiting for the expiration cleanup to reclaim them.
    """
    result = await db.execute(select(Job).where(Job.public_id == public_id))
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not allowed to delete this job")

    job_id = job.id
    artifacts_result = await db.execute(select(Artifact).where(Artifact.job_id == job_id))
    artifacts = artifacts_result.scalars().all()
    for artifact in artifacts:
        delete_storage_file(artifact.storage_path)
        await db.delete(artifact)

    await db.delete(job)
    delete_job_storage(job_id)
    await db.commit()
