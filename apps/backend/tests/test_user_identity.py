"""Tests for explicit user identity (prof feedback).

Every user gets a sequential running number; jobs carry the submitter's number
and spaces carry the creator's public id + number, so everything is explicitly
attributable to a user.
"""

import uuid

import pytest

from app.db.models import Space, User


async def _make_user(db, *, role="space_creator") -> User:
    unique = uuid.uuid4().hex
    user = User(subject_id=f"sub-{unique}", idp="test", email=f"{unique}@test.com", role=role)
    db.add(user)
    await db.flush()
    return user


async def _seed_space(db, owner: User) -> Space:
    unique = uuid.uuid4().hex
    space = Space(
        slug=f"s-{unique}",
        name="S",
        description="d",
        task_type="text",
        input_types=[],
        output_types=[],
        container_image="img:latest",
        ui_config={},
        runner_config={},
        visibility="PUBLIC",
        status="PUBLISHED",
        owner_id=owner.id,
    )
    db.add(space)
    await db.commit()
    return space


# ---------------------------------------------------------------------------
# user_number assignment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_users_get_sequential_numbers(db_session):
    u1 = await _make_user(db_session)
    u2 = await _make_user(db_session)
    await db_session.commit()
    assert u1.user_number == 1
    assert u2.user_number == 2


@pytest.mark.asyncio
async def test_users_created_in_one_flush_get_distinct_numbers(db_session):
    """A batch insert in a single flush must still get contiguous, unique numbers."""
    users = [
        User(subject_id=f"s-{i}-{uuid.uuid4().hex}", idp="test", email=f"{i}-{uuid.uuid4().hex}@test.com", role="end_user")
        for i in range(3)
    ]
    db_session.add_all(users)
    await db_session.commit()
    assert sorted(u.user_number for u in users) == [1, 2, 3]


@pytest.mark.asyncio
async def test_me_exposes_user_number(client):
    resp = await client.get("/me")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["user_number"], int)
    assert body["user_number"] >= 1


@pytest.mark.asyncio
async def test_admin_users_expose_user_number(client, db_session):
    await _make_user(db_session, role="end_user")
    await db_session.commit()
    resp = await client.get("/admin/users")
    assert resp.status_code == 200
    assert all(isinstance(u["user_number"], int) for u in resp.json())


# ---------------------------------------------------------------------------
# Spaces expose the creator's identity
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_space_detail_exposes_creator_public_id_and_number(client, db_session):
    owner = await _make_user(db_session)
    await db_session.commit()
    space = await _seed_space(db_session, owner)

    resp = await client.get(f"/spaces/{space.public_id}")
    assert resp.status_code == 200
    body = resp.json()
    # owner_id is now the creator's public UUID, not the internal integer.
    assert body["owner_id"] == str(owner.public_id)
    assert body["owner_number"] == owner.user_number


@pytest.mark.asyncio
async def test_public_catalog_exposes_creator(client, db_session):
    owner = await _make_user(db_session)
    await db_session.commit()
    await _seed_space(db_session, owner)

    resp = await client.get("/spaces")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["owner_id"] == str(owner.public_id)
    assert data[0]["owner_number"] == owner.user_number


# ---------------------------------------------------------------------------
# Jobs carry the submitter's number
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_exposes_user_number(client, seed_job):
    resp = await client.get(f"/jobs/{seed_job.public_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["user_number"], int)
    assert body["user_number"] >= 1


# ---------------------------------------------------------------------------
# Admin can reassign ownership by the target user's public id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_reassign_owner_by_public_id(client, db_session):
    owner = await _make_user(db_session)
    new_owner = await _make_user(db_session)
    await db_session.commit()
    space = await _seed_space(db_session, owner)

    resp = await client.patch(
        f"/admin/spaces/{space.public_id}",
        json={"owner_id": str(new_owner.public_id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["owner_id"] == str(new_owner.public_id)
    assert body["owner_number"] == new_owner.user_number


@pytest.mark.asyncio
async def test_admin_reassign_owner_unknown_returns_400(client, db_session):
    owner = await _make_user(db_session)
    await db_session.commit()
    space = await _seed_space(db_session, owner)

    resp = await client.patch(
        f"/admin/spaces/{space.public_id}",
        json={"owner_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 400
