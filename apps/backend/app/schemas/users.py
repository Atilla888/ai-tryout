from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserRead(BaseModel):
    """User profile returned by the /me endpoint. The internal integer id is hidden;
    the public UUID is exposed as 'id'."""
    id: UUID = Field(validation_alias="public_id")
    subject_id: str
    idp: str
    email: str
    display_name: str | None
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
