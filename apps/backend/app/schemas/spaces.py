"""Pydantic request/response schemas for creating, updating, and reading spaces."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import OrmBase


class SpaceListItem(OrmBase):
    """One space as it appears in a catalog list — public fields only, no config."""
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
    # Creator identity: the owner's public UUID and short running number.
    owner_id: UUID = Field(validation_alias="owner_public_id")
    owner_number: int


class SpaceDetail(OrmBase):
    """Full public view of a single space, including UI and runner config."""
    id: UUID = Field(validation_alias="public_id")
    name: str
    slug: str
    description: str
    task_type: str
    input_types: list[str]
    output_types: list[str]
    # Creator identity: the owner's public UUID and short running number
    # (owner_id was previously the internal integer row id — now the public UUID).
    owner_id: UUID = Field(validation_alias="owner_public_id")
    owner_number: int
    container_image: str
    ui_config: dict[str, Any]
    runner_config: dict[str, Any]
    visibility: str
    status: str
    created_at: datetime


class SpaceCreate(BaseModel):
    """Body for creating a space. Starts as private draft unless you say otherwise."""
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
    """Fields a creator may update on their own space — all optional for partial updates."""
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
    """Admin-only space update — adds reassigning ownership on top of SpaceUpdate."""
    # Reassign ownership by the target user's public UUID (resolved to the
    # internal row id in the router).
    owner_id: UUID | None = None


class SpaceRead(BaseModel):
    """Full space returned to its owner or an admin, including the creator's public id/number."""
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
    # Creator identity: the owner's public UUID and short running number.
    owner_id: UUID = Field(validation_alias="owner_public_id")
    owner_number: int

    model_config = ConfigDict(from_attributes=True)
