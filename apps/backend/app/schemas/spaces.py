from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import OrmBase


class SpaceListItem(OrmBase):
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
    # Reassign ownership by the target user's public UUID (resolved to the
    # internal row id in the router).
    owner_id: UUID | None = None


class SpaceRead(BaseModel):
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
