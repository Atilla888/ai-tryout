from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class SpaceListItem(BaseModel):
    """Returned by GET /spaces"""
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    task_type: str
    input_types: Any
    output_types: Any

    model_config = {"from_attributes": True}


class SpaceDetail(SpaceListItem):
    """Returned by GET /spaces/{space_id}"""
    container_image: str
    resource_requirements: Any
    ui_config: Any
    runner_config: Any
    visibility: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
