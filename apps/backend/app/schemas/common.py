"""Shared Pydantic base models and common response schemas."""

from pydantic import BaseModel, ConfigDict


class OrmBase(BaseModel):
    """Base for response models read straight from ORM objects."""
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    """Response returned by the health-check endpoint."""
    status: str
