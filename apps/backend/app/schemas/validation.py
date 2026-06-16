from pydantic import BaseModel


class FieldError(BaseModel):
    """One thing wrong with the space config."""
    field: str
    message: str


class ValidationResult(BaseModel):
    """Answer from POST /creator/spaces/{id}/validate."""
    valid: bool
    errors: list[FieldError]
