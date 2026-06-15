from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserRead(BaseModel):
    id: UUID = Field(validation_alias="public_id")
    subject_id: str
    idp: str
    email: str
    display_name: str | None
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
