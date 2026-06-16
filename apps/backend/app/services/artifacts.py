from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Artifact
from app.services.storage import resolve_storage_path


async def get_artifact_by_public_id_service(
    db: AsyncSession, public_id: UUID
) -> Artifact | None:
    result = await db.execute(
        select(Artifact)
        .where(Artifact.public_id == public_id)
    )
    return result.scalar_one_or_none()


async def get_artifact_by_id_service(
    db: AsyncSession, artifact_id: int
) -> Artifact | None:
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    return result.scalar_one_or_none()


async def list_artifacts_by_job_id_service(
    db: AsyncSession, job_id: int
) -> list[Artifact]:
    result = await db.execute(
        select(Artifact)
        .where(Artifact.job_id == job_id)
        .order_by(Artifact.created_at)
    )
    return list(result.scalars().all())


def artifact_absolute_path(artifact: Artifact) -> Path:
    return resolve_storage_path(artifact.storage_path)


def ensure_artifact_available(artifact: Artifact) -> None:
    """Raise if the file expired or is missing from disk."""
    if artifact.expires_at is not None:
        expires = artifact.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= datetime.now(timezone.utc):
            raise FileNotFoundError("Artifact expired")

    path = artifact_absolute_path(artifact)
    if not path.is_file():
        raise FileNotFoundError("Artifact file missing on disk")
