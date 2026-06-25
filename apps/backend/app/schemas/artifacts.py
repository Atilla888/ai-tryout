from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ArtifactRead(BaseModel):
    """File metadata for the public API. Download and preview use separate routes."""
    id: UUID
    artifact_type: str
    file_name: str
    content_type: str
    size_bytes: int
    storage_path: str
    preview_supported: bool
    created_at: datetime
    expires_at: datetime | None
    job_id: UUID
