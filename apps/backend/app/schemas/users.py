from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.schemas.common import OrmBase


class UserRead(OrmBase):
    id: UUID
    subject_id: str
    idp: str
    email: EmailStr
    display_name: str | None
    role: str
    created_at: datetime


class UserCreate(BaseModel):
    subject_id: str
    idp: str
    email: EmailStr
    display_name: str | None = None
    role: str = "user"
