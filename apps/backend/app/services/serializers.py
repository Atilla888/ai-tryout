from uuid import UUID

from app.db.models import Artifact, Job
from app.schemas.artifacts import ArtifactRead
from app.schemas.jobs import JobRead, JobStatus, JobSubmitResponse


def job_to_read(job: Job) -> JobRead:
    """Shape a job for public API responses (UUIDs, not internal ids)."""
    return JobRead(
        id=job.public_id,
        status=JobStatus(job.status),
        progress_percent=job.progress_percent,
        progress_message=job.progress_message,
        queue_position=job.queue_position,
        error_code=job.error_code,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        cancelled_at=job.cancelled_at,
        expires_at=job.expires_at,
        space_id=job.space.public_id,
        space_name=job.space.name if job.space else None,
        user_id=job.user.public_id,
        user_number=job.user.user_number,
    )


def job_to_submit_response(job: Job) -> JobSubmitResponse:
    return JobSubmitResponse(
        id=job.public_id,
        status=JobStatus(job.status),
        queue_position=job.queue_position,
    )


def artifact_to_read(artifact: Artifact, *, job_public_id: UUID | None = None) -> ArtifactRead:
    resolved_job_public_id = job_public_id
    if resolved_job_public_id is None:
        if artifact.job is not None:
            resolved_job_public_id = artifact.job.public_id
        else:
            raise ValueError("Need job_public_id or a loaded artifact.job")

    return ArtifactRead(
        id=artifact.public_id,
        artifact_type=artifact.artifact_type,
        file_name=artifact.file_name,
        content_type=artifact.content_type,
        size_bytes=artifact.size_bytes,
        storage_path=artifact.storage_path,
        preview_supported=artifact.preview_supported,
        created_at=artifact.created_at,
        expires_at=artifact.expires_at,
        job_id=resolved_job_public_id,
    )
