from pydantic import BaseModel, ConfigDict


class OrmBase(BaseModel):
    """Shared base with from_attributes=True so Pydantic can read SQLAlchemy ORM instances directly."""
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    status: str
