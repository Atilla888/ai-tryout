"""Unit tests for app.services.validation.validate_space_config.

These exercise the branching validation of ``ui_config`` and ``runner_config``
with valid, borderline, and error cases (Foliensatz 08). The validator only
reads ``ui_config``, ``runner_config`` and ``container_image`` off the Space, so
the tests build transient (non-persisted) Space objects and never touch the DB.
"""

import pytest

from app.db.models import Space
from app.services.validation import validate_space_config


# helpers

def _space(ui_config, runner_config=None, container_image="example/image:latest"):
    """Build a transient Space with just the fields the validator inspects."""
    return Space(
        ui_config=ui_config,
        runner_config=runner_config if runner_config is not None else {},
        container_image=container_image,
    )


def _valid_input(**overrides):
    """A minimal valid input definition; override single keys per test."""
    base = {"name": "prompt", "type": "text", "label": "Prompt"}
    base.update(overrides)
    return base


def _error_fields(result):
    return {error.field for error in result.errors}


# positive / happy path

def test_minimal_valid_config_is_valid():
    result = validate_space_config(_space({"inputs": [_valid_input()]}))
    assert result.valid is True
    assert result.errors == []


def test_select_input_with_options_is_valid():
    space = _space(
        {"inputs": [_valid_input(type="select", options=["a", "b"])]}
    )
    result = validate_space_config(space)
    assert result.valid is True


def test_multiple_distinct_input_names_are_valid():
    space = _space(
        {
            "inputs": [
                _valid_input(name="prompt", label="Prompt"),
                _valid_input(name="seed", type="number", label="Seed"),
            ]
        }
    )
    result = validate_space_config(space)
    assert result.valid is True


# ui_config.inputs container

def test_missing_inputs_key_is_invalid():
    result = validate_space_config(_space({}))
    assert result.valid is False
    assert "ui_config.inputs" in _error_fields(result)


def test_inputs_not_a_list_is_invalid():
    result = validate_space_config(_space({"inputs": {"name": "x"}}))
    assert result.valid is False
    assert "ui_config.inputs" in _error_fields(result)


def test_empty_inputs_list_is_invalid():
    result = validate_space_config(_space({"inputs": []}))
    assert result.valid is False
    assert "ui_config.inputs" in _error_fields(result)


def test_input_must_be_an_object():
    result = validate_space_config(_space({"inputs": ["not-an-object"]}))
    assert result.valid is False
    assert "ui_config.inputs[0]" in _error_fields(result)


# input.name

def test_missing_name_is_invalid():
    bad = _valid_input()
    del bad["name"]
    result = validate_space_config(_space({"inputs": [bad]}))
    assert result.valid is False
    assert "ui_config.inputs[0].name" in _error_fields(result)


def test_name_starting_with_digit_is_invalid():
    result = validate_space_config(_space({"inputs": [_valid_input(name="1abc")]}))
    assert result.valid is False
    assert "ui_config.inputs[0].name" in _error_fields(result)


def test_name_with_hyphen_is_invalid():
    result = validate_space_config(_space({"inputs": [_valid_input(name="a-b")]}))
    assert result.valid is False
    assert "ui_config.inputs[0].name" in _error_fields(result)


def test_duplicate_input_name_is_invalid():
    space = _space(
        {
            "inputs": [
                _valid_input(name="prompt"),
                _valid_input(name="prompt", label="Second"),
            ]
        }
    )
    result = validate_space_config(space)
    assert result.valid is False
    assert "ui_config.inputs[1].name" in _error_fields(result)


# input.type

def test_missing_type_is_invalid():
    bad = _valid_input()
    del bad["type"]
    result = validate_space_config(_space({"inputs": [bad]}))
    assert result.valid is False
    assert "ui_config.inputs[0].type" in _error_fields(result)


def test_unknown_type_is_invalid():
    result = validate_space_config(_space({"inputs": [_valid_input(type="video")]}))
    assert result.valid is False
    assert "ui_config.inputs[0].type" in _error_fields(result)


def test_select_without_options_is_invalid():
    result = validate_space_config(_space({"inputs": [_valid_input(type="select")]}))
    assert result.valid is False
    assert "ui_config.inputs[0].options" in _error_fields(result)


def test_select_with_empty_options_is_invalid():
    space = _space({"inputs": [_valid_input(type="select", options=[])]})
    result = validate_space_config(space)
    assert result.valid is False
    assert "ui_config.inputs[0].options" in _error_fields(result)


def test_select_with_empty_string_option_is_invalid():
    space = _space({"inputs": [_valid_input(type="select", options=["ok", ""])]})
    result = validate_space_config(space)
    assert result.valid is False
    assert "ui_config.inputs[0].options" in _error_fields(result)


# input.label / required

def test_missing_label_is_invalid():
    bad = _valid_input()
    del bad["label"]
    result = validate_space_config(_space({"inputs": [bad]}))
    assert result.valid is False
    assert "ui_config.inputs[0].label" in _error_fields(result)


def test_required_not_a_bool_is_invalid():
    result = validate_space_config(_space({"inputs": [_valid_input(required="yes")]}))
    assert result.valid is False
    assert "ui_config.inputs[0].required" in _error_fields(result)


def test_required_bool_is_valid():
    result = validate_space_config(_space({"inputs": [_valid_input(required=True)]}))
    assert result.valid is True


# runner_config / container_image

def test_empty_container_image_is_invalid():
    space = _space({"inputs": [_valid_input()]}, container_image="   ")
    result = validate_space_config(space)
    assert result.valid is False
    assert "container_image" in _error_fields(result)


def test_timeout_seconds_as_bool_is_invalid():
    space = _space({"inputs": [_valid_input()]}, runner_config={"timeout_seconds": True})
    result = validate_space_config(space)
    assert result.valid is False
    assert "runner_config.timeout_seconds" in _error_fields(result)


def test_timeout_seconds_zero_is_invalid():
    space = _space({"inputs": [_valid_input()]}, runner_config={"timeout_seconds": 0})
    result = validate_space_config(space)
    assert result.valid is False
    assert "runner_config.timeout_seconds" in _error_fields(result)


def test_timeout_seconds_above_max_is_invalid():
    space = _space({"inputs": [_valid_input()]}, runner_config={"timeout_seconds": 86401})
    result = validate_space_config(space)
    assert result.valid is False
    assert "runner_config.timeout_seconds" in _error_fields(result)


def test_memory_mb_as_bool_is_invalid():
    space = _space({"inputs": [_valid_input()]}, runner_config={"memory_mb": False})
    result = validate_space_config(space)
    assert result.valid is False
    assert "runner_config.memory_mb" in _error_fields(result)


def test_memory_mb_below_min_is_invalid():
    space = _space({"inputs": [_valid_input()]}, runner_config={"memory_mb": 63})
    result = validate_space_config(space)
    assert result.valid is False
    assert "runner_config.memory_mb" in _error_fields(result)


def test_memory_mb_above_max_is_invalid():
    space = _space({"inputs": [_valid_input()]}, runner_config={"memory_mb": 65537})
    result = validate_space_config(space)
    assert result.valid is False
    assert "runner_config.memory_mb" in _error_fields(result)


# borderline values that must stay valid

@pytest.mark.parametrize("timeout", [1, 86400])
def test_timeout_seconds_boundaries_are_valid(timeout):
    space = _space({"inputs": [_valid_input()]}, runner_config={"timeout_seconds": timeout})
    result = validate_space_config(space)
    assert result.valid is True


@pytest.mark.parametrize("memory", [64, 65536])
def test_memory_mb_boundaries_are_valid(memory):
    space = _space({"inputs": [_valid_input()]}, runner_config={"memory_mb": memory})
    result = validate_space_config(space)
    assert result.valid is True
