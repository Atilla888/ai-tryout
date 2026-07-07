"""Background maintenance: enforce the job/artifact retention lifecycle (D3).

Jobs and their artifacts carry an ``expires_at`` set 14 days out (see
``JOB_RETENTION_DAYS`` in ``app.services.jobs``). Once that passes, the job is
marked ``EXPIRED`` and its artifact files are removed from disk so storage does
not grow without bound.

``EXPIRED`` is a *system-applied* terminal state. It deliberately does not go
through the user-facing state machine in ``app.services.job_transitions`` — there
is no allowed transition into ``EXPIRED`` for runners or users — so this module
sets the status directly.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import delete as sql_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Artifact, Job
from app.schemas.jobs import JobStatus
from app.services.storage import delete_job_storage, delete_storage_file


@dataclass
class CleanupResult:
    """Counts of what a cleanup pass changed: jobs expired and artifacts removed."""
    jobs_expired: int = 0
    artifacts_removed: int = 0


async def cleanup_expired_jobs_and_artifacts(db: AsyncSession) -> CleanupResult:
    """Mark jobs past retention as EXPIRED, delete their (and any orphaned) artifact files from disk and rows from the DB, and commit."""
    now = datetime.now(timezone.utc)
    result = CleanupResult()

    # 1. Find jobs whose retention window has passed and that are not already expired.
    expired_jobs = (
        await db.execute(
            select(Job).where(
                Job.expires_at.is_not(None),
                Job.expires_at < now,
                Job.status != JobStatus.EXPIRED.value,
            )
        )
    ).scalars().all()

    for job in expired_jobs:
        # Drop the artifact files for this job (inputs and outputs) from disk.
        artifacts = (
            await db.execute(select(Artifact).where(Artifact.job_id == job.id))
        ).scalars().all()
        for artifact in artifacts:
            delete_storage_file(artifact.storage_path)
        delete_job_storage(job.id)

        if artifacts:
            await db.execute(sql_delete(Artifact).where(Artifact.job_id == job.id))
            result.artifacts_removed += len(artifacts)

        job.status = JobStatus.EXPIRED.value
        result.jobs_expired += 1

    # 2. Safety net: any leftover artifact whose own expires_at has passed
    #    (e.g. artifact deleted from a non-expired job, or a future policy where
    #    artifact retention is shorter than job retention).
    orphan_artifacts = (
        await db.execute(
            select(Artifact).where(
                Artifact.expires_at.is_not(None),
                Artifact.expires_at < now,
            )
        )
    ).scalars().all()

    for artifact in orphan_artifacts:
        delete_storage_file(artifact.storage_path)

    if orphan_artifacts:
        orphan_ids = [artifact.id for artifact in orphan_artifacts]
        await db.execute(sql_delete(Artifact).where(Artifact.id.in_(orphan_ids)))
        result.artifacts_removed += len(orphan_artifacts)

    await db.commit()
    return result
