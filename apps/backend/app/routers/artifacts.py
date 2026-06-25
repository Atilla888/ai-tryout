from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.artifacts import (
    artifact_absolute_path,
    ensure_artifact_available,
    get_artifact_by_public_id_service,
)

router = APIRouter(prefix="/artifacts", tags=["artifacts"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.get("/{artifact_id}/preview")
async def preview_artifact(db: db_dependency, artifact_id: UUID) -> FileResponse:
    artifact = await get_artifact_by_public_id_service(db, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    try:
        ensure_artifact_available(artifact)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    path = artifact_absolute_path(artifact)
    return FileResponse(
        path=path,
        media_type=artifact.content_type,
        filename=artifact.file_name,
    )


@router.get("/{artifact_id}/download")
async def download_artifact(db: db_dependency, artifact_id: UUID) -> FileResponse:
    artifact = await get_artifact_by_public_id_service(db, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    try:
        ensure_artifact_available(artifact)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    path = artifact_absolute_path(artifact)
    return FileResponse(
        path=path,
        media_type=artifact.content_type,
        filename=artifact.file_name,
        content_disposition_type="attachment",
    )
