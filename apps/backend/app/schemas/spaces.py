from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import OrmBase


class SpaceListItem(OrmBase):
    """Lightweight space representation for list/card views."""

    id: UUID = Field(validation_alias="public_id")
    public_id: UUID
    name: str
    slug: str
    description: str
    task_type: str
    input_types: list[str]
    output_types: list[str]
    status: str
    visibility: str


class SpaceDetail(OrmBase):
    """Full space representation including UI and runner config."""

    id: UUID = Field(validation_alias="public_id")
    name: str
    slug: str
    description: str
    task_type: str
    input_types: list[str]
    output_types: list[str]
    owner_id: int
    container_image: str
    ui_config: dict[str, Any]
    runner_config: dict[str, Any]
    visibility: str
    status: str
    created_at: datetime


class SpaceCreate(BaseModel):
    """Request body for POST /creator/spaces. Defaults to PRIVATE visibility and DRAFT status."""
    slug: str
    name: str
    description: str
    task_type: str
    input_types: list[str]
    output_types: list[str]
    container_image: str
    ui_config: dict[str, Any]
    runner_config: dict[str, Any]
    visibility: str = "PRIVATE"
    status: str = "DRAFT"


class SpaceUpdate(BaseModel):
    """Partial update body for PATCH /creator/spaces/{id}. All fields are optional."""
    name: str | None = None
    description: str | None = None
    task_type: str | None = None
    input_types: list[str] | None = None
    output_types: list[str] | None = None
    container_image: str | None = None
    ui_config: dict[str, Any] | None = None
    runner_config: dict[str, Any] | None = None
    visibility: str | None = None
    status: str | None = None


class AdminSpaceUpdate(SpaceUpdate):
    """Extends SpaceUpdate to allow admins to reassign ownership via owner_id."""
    owner_id: int | None = None


class SpaceRead(BaseModel):
    """Full space representation returned to the creator/admin after write operations."""
    id: UUID = Field(validation_alias="public_id")
    created_at: datetime
    slug: str
    name: str
    description: str
    task_type: str
    input_types: list[str]
    output_types: list[str]
    container_image: str
    ui_config: dict[str, Any]
    runner_config: dict[str, Any]
    visibility: str
    status: str
    owner_id: int

    model_config = ConfigDict(from_attributes= True)
