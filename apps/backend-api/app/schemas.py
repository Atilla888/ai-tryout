"""Pydantic request/response schemas — API layer only.

Keep database mapping in models.py.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import ArtifactType, JobStatus, SpaceStatus, SpaceVisibility, UserRole


# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------


class _OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------


class UserRead(_OrmBase):
    id: uuid.UUID
    display_name: str
    email: EmailStr
    role: UserRole
    created_at: datetime


class UserCreate(BaseModel):
    display_name: str
    email: EmailStr
    role: UserRole = UserRole.user


# ---------------------------------------------------------------------------
# Space schemas
# ---------------------------------------------------------------------------


class SpaceListItem(_OrmBase):
    """Lightweight space representation for the landing-page card grid."""

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    task_type: str
    input_types: list
    output_types: list
    status: SpaceStatus
    visibility: SpaceVisibility


class SpaceDetail(_OrmBase):
    """Full space representation including UI and runner config."""

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    task_type: str
    input_types: list
    output_types: list
    owner_id: uuid.UUID | None
    container_image: str | None
    resource_requirements: dict
    ui_config: dict
    runner_config: dict
    visibility: SpaceVisibility
    status: SpaceStatus
    created_at: datetime
    updated_at: datetime


class SpaceCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    task_type: str
    input_types: list = []
    output_types: list = []
    container_image: str | None = None
    resource_requirements: dict = {}
    ui_config: dict = {}
    runner_config: dict = {}
    visibility: SpaceVisibility = SpaceVisibility.public


class SpaceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    task_type: str | None = None
    input_types: list | None = None
    output_types: list | None = None
    container_image: str | None = None
    resource_requirements: dict | None = None
    ui_config: dict | None = None
    runner_config: dict | None = None
    visibility: SpaceVisibility | None = None
    status: SpaceStatus | None = None


# ---------------------------------------------------------------------------
# Job schemas
# ---------------------------------------------------------------------------


class JobCreate(BaseModel):
    input_payload: dict = {}


class JobRead(_OrmBase):
    id: uuid.UUID
    space_id: uuid.UUID
    user_id: uuid.UUID | None
    status: JobStatus
    queue_position: int | None
    progress_percent: int | None
    progress_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    expires_at: datetime | None
    error_code: str | None
    error_message: str | None


class JobSubmitResponse(BaseModel):
    id: uuid.UUID
    status: JobStatus
    queue_position: int | None


class JobProgressUpdate(BaseModel):
    """Internal: model runner reports progress."""

    progress_percent: int
    message: str | None = None


class JobFailUpdate(BaseModel):
    """Internal: model runner reports failure."""

    error_code: str
    error_message: str


# ---------------------------------------------------------------------------
# Artifact schemas
# ---------------------------------------------------------------------------


class ArtifactRead(_OrmBase):
    id: uuid.UUID
    job_id: uuid.UUID
    user_id: uuid.UUID | None
    artifact_type: ArtifactType
    file_name: str
    content_type: str
    size_bytes: int | None
    preview_supported: bool
    created_at: datetime
    expires_at: datetime | None


# ---------------------------------------------------------------------------
# Health schema
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
