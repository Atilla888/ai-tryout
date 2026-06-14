from pydantic import BaseModel


class FieldError(BaseModel):
    field: str
    message: str


class ValidationResult(BaseModel):
    valid: bool
    errors: list[FieldError]
