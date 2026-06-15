from pydantic import BaseModel


class FieldError(BaseModel):
    """A single validation failure with the dot-path to the offending field and an error message."""
    field: str
    message: str


class ValidationResult(BaseModel):
    """Returned by the /creator/spaces/{id}/validate endpoint so creators can see
    all problems at once before attempting to publish."""
    valid: bool
    errors: list[FieldError]
