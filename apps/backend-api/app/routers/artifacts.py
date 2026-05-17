"""Artifact preview and download endpoints — /artifacts/{artifact_id}."""

import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.dependencies import DbSession
from app.models import Artifact

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


async def _get_artifact_or_404(artifact_id: uuid.UUID, db: DbSession) -> Artifact:
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@router.get("/{artifact_id}/preview")
async def preview_artifact(artifact_id: uuid.UUID, db: DbSession) -> FileResponse:
    """Serve the artifact file for in-browser preview."""
    artifact = await _get_artifact_or_404(artifact_id, db)
    return FileResponse(
        path=artifact.storage_path,
        media_type=artifact.content_type,
        filename=artifact.file_name,
    )


@router.get("/{artifact_id}/download")
async def download_artifact(artifact_id: uuid.UUID, db: DbSession) -> FileResponse:
    """Serve the artifact file as an attachment download."""
    artifact = await _get_artifact_or_404(artifact_id, db)
    return FileResponse(
        path=artifact.storage_path,
        media_type=artifact.content_type,
        filename=artifact.file_name,
        content_disposition_type="attachment",
    )
