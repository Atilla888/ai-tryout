from typing import Any
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class SpaceCreate(BaseModel):
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

class SpaceRead(BaseModel):
    id: UUID
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
    owner_id: UUID

    model_config = {
        "from_attributes": True # enables obj attribute access like space.id, instead of dict like space["id"] 
    }