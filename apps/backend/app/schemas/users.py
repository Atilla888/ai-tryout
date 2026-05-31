from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UserRead(BaseModel):
    id: UUID
    subject_id: str
    idp: str
    email: str
    display_name: str | None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}
