"""Integration tests for the admin API (router/admin.py)."""

import uuid

import pytest

from app.db.models import Space, User
from app.core.auth import get_current_user
from app.db.session import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_space(db_session, *, visibility="PUBLIC", status="PUBLISHED") -> Space:
    unique = uuid.uuid4().hex
    owner = User(
        subject_id=f"owner-{unique}",
        idp="test",
        email=f"owner-{unique}@test.com",
        role="space_creator",
    )
    db_session.add(owner)
    await db_session.flush()
    space = Space(
        slug=f"s-{unique}",
        name="Admin Test Space",
        description="desc",
        task_type="text",
        input_types=[],
        output_types=[],
        container_image="img:latest",
        ui_config={},
        runner_config={},
        visibility=visibility,
        status=status,
        owner_id=owner.id,
    )
    db_session.add(space)
    await db_session.commit()
    return space


def _non_admin_client(db_session):
    """Returns a context manager yielding an HTTPX client authenticated as a plain end_user."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    unique = uuid.uuid4().hex

    user = User(
        subject_id=f"non-admin-{unique}",
        idp="test",
        email=f"non-admin-{unique}@test.com",
        role="end_user",
    )

    async def _get_user():
        return user

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _get_user
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# GET /admin/spaces
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_list_spaces_empty(client):
    response = await client.get("/admin/spaces")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_admin_list_spaces_returns_all(client, db_session):
    await _seed_space(db_session, visibility="PUBLIC", status="PUBLISHED")
    await _seed_space(db_session, visibility="PRIVATE", status="DRAFT")
    response = await client.get("/admin/spaces")
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_admin_list_spaces_non_admin_returns_403(db_session):
    from app.main import app
    async with _non_admin_client(db_session) as c:
        response = await c.get("/admin/spaces")
    app.dependency_overrides.clear()
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /admin/spaces/{space_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_update_space_status(client, db_session):
    space = await _seed_space(db_session, status="DRAFT")
    response = await client.patch(
        f"/admin/spaces/{space.public_id}",
        json={"status": "PUBLISHED"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "PUBLISHED"


@pytest.mark.asyncio
async def test_admin_update_space_visibility(client, db_session):
    space = await _seed_space(db_session, visibility="PRIVATE")
    response = await client.patch(
        f"/admin/spaces/{space.public_id}",
        json={"visibility": "PUBLIC"},
    )
    assert response.status_code == 200
    assert response.json()["visibility"] == "PUBLIC"


@pytest.mark.asyncio
async def test_admin_update_space_not_found_returns_404(client):
    response = await client.patch(
        f"/admin/spaces/{uuid.uuid4()}",
        json={"status": "PUBLISHED"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_update_space_non_admin_returns_403(db_session):
    space = await _seed_space(db_session)
    from app.main import app
    async with _non_admin_client(db_session) as c:
        response = await c.patch(f"/admin/spaces/{space.public_id}", json={"status": "DRAFT"})
    app.dependency_overrides.clear()
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /admin/spaces/{space_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_delete_space_returns_204(client, db_session):
    space = await _seed_space(db_session)
    response = await client.delete(f"/admin/spaces/{space.public_id}")
    assert response.status_code == 204

    # Should be gone now
    get_resp = await client.get(f"/spaces/{space.public_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_delete_space_not_found_returns_404(client):
    response = await client.delete(f"/admin/spaces/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_delete_space_non_admin_returns_403(db_session):
    space = await _seed_space(db_session)
    from app.main import app
    async with _non_admin_client(db_session) as c:
        response = await c.delete(f"/admin/spaces/{space.public_id}")
    app.dependency_overrides.clear()
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_list_users_empty(client):
    response = await client.get("/admin/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_admin_list_users_includes_seeded_users(client, db_session):
    unique = uuid.uuid4().hex
    user = User(
        subject_id=f"listed-{unique}",
        idp="test",
        email=f"listed-{unique}@test.com",
        role="end_user",
    )
    db_session.add(user)
    await db_session.commit()

    response = await client.get("/admin/users")
    assert response.status_code == 200
    emails = [u["email"] for u in response.json()]
    assert f"listed-{unique}@test.com" in emails


@pytest.mark.asyncio
async def test_admin_list_users_non_admin_returns_403(db_session):
    from app.main import app
    async with _non_admin_client(db_session) as c:
        response = await c.get("/admin/users")
    app.dependency_overrides.clear()
    assert response.status_code == 403
