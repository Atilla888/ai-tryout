"""Unit tests for the pure auth helpers in app.core.auth.

``_bearer_token`` and ``map_realm_roles_to_role`` contain branching logic that
has no Keycloak dependency, so they can be unit-tested directly.
"""

import pytest
from fastapi import HTTPException, status

from app.core.auth import _bearer_token, map_realm_roles_to_role


# _bearer_token

def test_bearer_token_returns_token_for_valid_header():
    assert _bearer_token("Bearer abc.def.ghi") == "abc.def.ghi"


def test_bearer_token_is_case_insensitive_on_scheme():
    assert _bearer_token("bearer token123") == "token123"


def test_bearer_token_strips_surrounding_whitespace():
    assert _bearer_token("Bearer   token123  ") == "token123"


def test_bearer_token_missing_header_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        _bearer_token(None)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_bearer_token_empty_header_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        _bearer_token("")
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_bearer_token_basic_scheme_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        _bearer_token("Basic xyz")
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_bearer_token_without_bearer_prefix_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        _bearer_token("token-without-scheme")
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


# map_realm_roles_to_role

def test_admin_role_maps_to_admin():
    assert map_realm_roles_to_role(["admin"]) == "admin"


def test_space_creator_role_maps_to_space_creator():
    assert map_realm_roles_to_role(["space_creator"]) == "space_creator"


def test_empty_roles_map_to_end_user():
    assert map_realm_roles_to_role([]) == "end_user"


def test_unknown_roles_map_to_end_user():
    assert map_realm_roles_to_role(["offline_access", "uma_authorization"]) == "end_user"


def test_admin_takes_precedence_over_space_creator():
    assert map_realm_roles_to_role(["space_creator", "admin"]) == "admin"
