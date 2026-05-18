from datetime import datetime
from typing import Any
from uuid import UUID
from enum import StrEnum
from pydantic import BaseModel


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class JobRead(BaseModel):
    id: UUID
    status: JobStatus
    progress_percent: int
    progress_message: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    cancelled_at: datetime | None
    expires_at: datetime | None
    input_payload: dict[str, Any]
    space_id: UUID
    user_id: UUID

    model_config = {
        "from_attributes": True
    }
