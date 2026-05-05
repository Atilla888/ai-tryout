"""Artifact preview and download endpoints — /artifacts/{artifact_id}."""

import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.dependencies import DbSession

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}/preview")
async def preview_artifact(artifact_id: uuid.UUID, db: DbSession) -> FileResponse:
    """Serve the artifact file for in-browser preview."""
    # TODO(S1-07): fetch artifact record, stream file with correct Content-Type
    raise HTTPException(status_code=404, detail="Artifact not found")


@router.get("/{artifact_id}/download")
async def download_artifact(artifact_id: uuid.UUID, db: DbSession) -> FileResponse:
    """Serve the artifact file as an attachment download."""
    # TODO(S1-07): fetch artifact record, stream file with Content-Disposition: attachment
    raise HTTPException(status_code=404, detail="Artifact not found")
