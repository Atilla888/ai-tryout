from pydantic import BaseModel, Field


class JobProgressUpdate(BaseModel):
    progress_percent: int = Field(ge=0, le=100)
    message: str | None = None


class JobFailUpdate(BaseModel):
    error_code: str | None = None
    error_message: str
