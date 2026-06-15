from pydantic import BaseModel, Field


class JobProgressUpdate(BaseModel):
    """Request body for the /internal/jobs/{id}/progress endpoint.
    progress_percent is enforced between 0 and 100."""
    progress_percent: int = Field(ge=0, le=100)
    message: str | None = None


class JobFailUpdate(BaseModel):
    """Request body for the /internal/jobs/{id}/fail endpoint."""
    error_code: str
    error_message: str
