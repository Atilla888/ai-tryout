from pydantic import BaseModel, ConfigDict


class OrmBase(BaseModel):
    """Lets Pydantic read fields straight off a SQLAlchemy model."""
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    status: str
