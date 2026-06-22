from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.jobs import JobStatus


class JobProgressUpdate(BaseModel):
    """Runner reporting how far along it is."""
    progress_percent: int = Field(ge=0, le=100)
    message: str | None = None


class JobFailUpdate(BaseModel):
    """Runner explaining why the job failed."""
    error_code: str
    error_message: str


class InternalJobRead(BaseModel):
    """Job as the orchestrator and runners see it — database ids, not UUIDs."""
    id: int
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
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class RunnerInputArtifact(BaseModel):
    """One uploaded INPUT file the runner can download and use (D4)."""
    id: int
    field_name: str | None = None
    file_name: str
    content_type: str
    size_bytes: int
    content_url: str


class RunnerInput(BaseModel):
    """Everything a runner needs to execute: the form payload plus input files (D4)."""
    job_id: int
    space_id: int
    input_payload: dict[str, Any]
    input_artifacts: list[RunnerInputArtifact] = Field(default_factory=list)


class JobExecutionData(BaseModel):
    """What the orchestrator needs to launch a worker for a job (spec 5.3, F2)."""
    job_id: int
    space_id: int
    space_public_id: str
    runner_image: str
    runner_config: dict[str, Any]
    input_reference: int


class InternalArtifactRead(BaseModel):
    """Artifact row right after an internal upload."""
    id: int
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
