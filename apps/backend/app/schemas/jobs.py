from datetime import datetime
from uuid import UUID

from enum import StrEnum
from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    """All possible states in the job lifecycle. CANCELLING is a transient state while
    the runner is notified; it should quickly move to CANCELLED."""
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
    """Returned immediately after a job is created so the frontend can navigate to the job page."""
    id: int
    public_id: UUID
    status: JobStatus
    queue_position: int | None = None


class JobRead(BaseModel):
    """Full job representation returned by the polling and history endpoints.
    space_name is denormalized here to avoid a second request from the frontend."""
    id: int
    public_id: UUID
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
    space_id: int
    space_name: str | None = None
    user_id: int

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    input_payload: dict = Field(default_factory=dict)
