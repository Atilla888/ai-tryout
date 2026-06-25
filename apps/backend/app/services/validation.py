import re
from typing import Any

from app.db.models import Space
from app.schemas.validation import FieldError, ValidationResult

_ALLOWED_INPUT_TYPES = {"text", "file", "number", "select"}
_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_ui_config(ui_config: dict[str, Any]) -> list[FieldError]:
    errors: list[FieldError] = []

    inputs = ui_config.get("inputs")
    if inputs is None:
        errors.append(FieldError(field="ui_config.inputs", message="'inputs' key is required"))
        return errors
    if not isinstance(inputs, list):
        errors.append(FieldError(field="ui_config.inputs", message="'inputs' must be a list"))
        return errors
    if len(inputs) == 0:
        errors.append(FieldError(field="ui_config.inputs", message="At least one input is required"))

    seen_names: set[str] = set()
    for i, item in enumerate(inputs):
        prefix = f"ui_config.inputs[{i}]"

        if not isinstance(item, dict):
            errors.append(FieldError(field=prefix, message="Each input must be an object"))
            continue

        name = item.get("name")
        if not name or not isinstance(name, str):
            errors.append(FieldError(field=f"{prefix}.name", message="'name' is required and must be a non-empty string"))
        elif not _NAME_RE.match(name):
            errors.append(FieldError(field=f"{prefix}.name", message="'name' must start with a letter or underscore and contain only letters, digits, or underscores"))
        elif name in seen_names:
            errors.append(FieldError(field=f"{prefix}.name", message=f"Duplicate input name '{name}'"))
        else:
            seen_names.add(name)

        input_type = item.get("type")
        if not input_type or not isinstance(input_type, str):
            errors.append(FieldError(field=f"{prefix}.type", message="'type' is required"))
        elif input_type not in _ALLOWED_INPUT_TYPES:
            errors.append(FieldError(field=f"{prefix}.type", message=f"'type' must be one of: {', '.join(sorted(_ALLOWED_INPUT_TYPES))}"))
        elif input_type == "select":
            options = item.get("options")
            if not isinstance(options, list) or len(options) == 0:
                errors.append(FieldError(field=f"{prefix}.options", message="'options' is required and must be a non-empty list for type 'select'"))
            elif not all(isinstance(o, str) and o for o in options):
                errors.append(FieldError(field=f"{prefix}.options", message="All 'options' entries must be non-empty strings"))

        label = item.get("label")
        if not label or not isinstance(label, str):
            errors.append(FieldError(field=f"{prefix}.label", message="'label' is required and must be a non-empty string"))

        required = item.get("required")
        if required is not None and not isinstance(required, bool):
            errors.append(FieldError(field=f"{prefix}.required", message="'required' must be a boolean"))

    return errors


def _validate_runner_config(runner_config: dict[str, Any], container_image: str) -> list[FieldError]:
    errors: list[FieldError] = []

    if not container_image or not container_image.strip():
        errors.append(FieldError(field="container_image", message="'container_image' must not be empty"))

    if not isinstance(runner_config, dict):
        errors.append(FieldError(field="runner_config", message="'runner_config' must be an object"))
        return errors

    timeout = runner_config.get("timeout_seconds")
    if timeout is not None:
        if not isinstance(timeout, int) or isinstance(timeout, bool):
            errors.append(FieldError(field="runner_config.timeout_seconds", message="'timeout_seconds' must be an integer"))
        elif not (1 <= timeout <= 86400):
            errors.append(FieldError(field="runner_config.timeout_seconds", message="'timeout_seconds' must be between 1 and 86400"))

    memory = runner_config.get("memory_mb")
    if memory is not None:
        if not isinstance(memory, int) or isinstance(memory, bool):
            errors.append(FieldError(field="runner_config.memory_mb", message="'memory_mb' must be an integer"))
        elif not (64 <= memory <= 65536):
            errors.append(FieldError(field="runner_config.memory_mb", message="'memory_mb' must be between 64 and 65536"))

    return errors


def validate_space_config(space: Space) -> ValidationResult:
    errors: list[FieldError] = []
    errors.extend(_validate_ui_config(space.ui_config or {}))
    errors.extend(_validate_runner_config(space.runner_config or {}, space.container_image or ""))
    return ValidationResult(valid=len(errors) == 0, errors=errors)
