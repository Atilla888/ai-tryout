"""Unit tests for app/services/users.py."""

import uuid

import pytest
from unittest.mock import AsyncMock, patch

from app.db.models import User
from app.services.users import (
    get_or_create_user_service,
    get_user_by_subject_service,
    list_users_service,
)


# ---------------------------------------------------------------------------
# list_users_service
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_users_empty(db_session):
    users = await list_users_service(db_session)
    assert users == []


@pytest.mark.asyncio
async def test_list_users_returns_all(db_session):
    for i in range(3):
        unique = uuid.uuid4().hex
        db_session.add(User(
            subject_id=f"sub-{unique}",
            idp="test",
            email=f"u{i}-{unique}@test.com",
            role="end_user",
        ))
    await db_session.commit()

    users = await list_users_service(db_session)
    assert len(users) == 3


# ---------------------------------------------------------------------------
# get_user_by_subject_service
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_user_by_subject_found(db_session):
    unique = uuid.uuid4().hex
    user = User(subject_id=f"sub-{unique}", idp="keycloak", email=f"u-{unique}@test.com", role="end_user")
    db_session.add(user)
    await db_session.commit()

    found = await get_user_by_subject_service(db_session, subject_id=f"sub-{unique}", idp="keycloak")
    assert found is not None
    assert found.email == f"u-{unique}@test.com"


@pytest.mark.asyncio
async def test_get_user_by_subject_not_found_returns_none(db_session):
    result = await get_user_by_subject_service(db_session, subject_id="nobody", idp="keycloak")
    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_subject_wrong_idp_returns_none(db_session):
    unique = uuid.uuid4().hex
    db_session.add(User(subject_id=f"sub-{unique}", idp="keycloak", email=f"u-{unique}@test.com", role="end_user"))
    await db_session.commit()

    result = await get_user_by_subject_service(db_session, subject_id=f"sub-{unique}", idp="other-idp")
    assert result is None


# ---------------------------------------------------------------------------
# get_or_create_user_service
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_or_create_creates_new_user(db_session):
    unique = uuid.uuid4().hex
    user = await get_or_create_user_service(
        db_session,
        subject_id=f"new-{unique}",
        email=f"new-{unique}@test.com",
        display_name="New User",
        role="end_user",
        idp="keycloak",
    )
    assert user.id is not None
    assert user.subject_id == f"new-{unique}"
    assert user.email == f"new-{unique}@test.com"


@pytest.mark.asyncio
async def test_get_or_create_returns_existing_user(db_session):
    unique = uuid.uuid4().hex
    first = await get_or_create_user_service(
        db_session,
        subject_id=f"existing-{unique}",
        email=f"existing-{unique}@test.com",
        display_name="Existing",
        role="end_user",
        idp="keycloak",
    )

    second = await get_or_create_user_service(
        db_session,
        subject_id=f"existing-{unique}",
        email=f"existing-{unique}@test.com",
        display_name="Existing",
        role="end_user",
        idp="keycloak",
    )

    assert first.id == second.id


@pytest.mark.asyncio
async def test_get_or_create_handles_concurrent_race(db_session):
    """If commit raises IntegrityError (race condition), the existing row is returned."""
    from sqlalchemy.exc import IntegrityError

    unique = uuid.uuid4().hex
    existing = User(
        subject_id=f"race-{unique}",
        idp="keycloak",
        email=f"race-{unique}@test.com",
        role="end_user",
    )
    db_session.add(existing)
    await db_session.commit()

    # Simulate a race: commit raises IntegrityError, then the subsequent lookup
    # finds the already-committed row.
    original_commit = db_session.commit

    call_count = 0

    async def _flaky_commit():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise IntegrityError("duplicate", {}, Exception())
        return await original_commit()

    with patch.object(db_session, "commit", side_effect=_flaky_commit):
        with patch.object(db_session, "rollback", new_callable=AsyncMock):
            result = await get_or_create_user_service(
                db_session,
                subject_id=f"race-{unique}",
                email=f"race-{unique}@test.com",
                display_name=None,
                role="end_user",
                idp="keycloak",
            )

    assert result.id == existing.id
