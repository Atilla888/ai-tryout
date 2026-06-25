from datetime import datetime
from uuid import UUID

from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field


class JobStatus(StrEnum):
    """Where a job is in its life. CANCELLING is brief — we move to CANCELLED right after."""
    QUEUED = "QUEUED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


TERMINAL_JOB_STATUSES = frozenset({
    JobStatus.SUCCEEDED,
    JobStatus.FAILED,
    JobStatus.CANCELLED,
    JobStatus.EXPIRED,
})

ACTIVE_JOB_STATUSES = frozenset({
    JobStatus.QUEUED,
    JobStatus.STARTING,
    JobStatus.RUNNING,
    JobStatus.CANCELLING,
})


class JobSubmitResponse(BaseModel):
    id: UUID
    status: JobStatus
    queue_position: int | None = None


class JobRead(BaseModel):
    """Full job for polling and history. Uses public UUIDs throughout."""
    id: UUID
    status: JobStatus
    progress_percent: int
    progress_message: str | None
    queue_position: int | None = None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    cancelled_at: datetime | None = None
    expires_at: datetime | None
    space_id: UUID
    space_name: str | None = None
    user_id: UUID


class JobCreate(BaseModel):
    input_payload: dict = Field(default_factory=dict)
