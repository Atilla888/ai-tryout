from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ArtifactRead(BaseModel):
    id: UUID = Field(validation_alias="public_id")
    artifact_type: str
    file_name: str
    content_type: str
    size_bytes: int
    storage_path: str
    preview_supported: bool
    created_at: datetime
    expires_at: datetime | None
    job_id: int

    model_config = ConfigDict(from_attributes=True)
