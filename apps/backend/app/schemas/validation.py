"""Pydantic schemas for space-config validation results and field-level errors."""

from pydantic import BaseModel


class FieldError(BaseModel):
    """A single field-level validation error."""
    field: str
    message: str


class ValidationResult(BaseModel):
    """Result of validating a payload — an overall flag plus any per-field errors."""
    valid: bool
    errors: list[FieldError]
