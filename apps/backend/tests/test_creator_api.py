"""Integration tests for the creator API (router/creator.py).

Covers: create space, list spaces, update space, validate config — and the 404/403
error branches that were previously uncovered.
"""

import uuid

import pytest

from app.db.models import Space, User


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------

def _space_payload(slug=None) -> dict:
    s = slug or f"slug-{uuid.uuid4().hex[:8]}"
    return {
        "slug": s,
        "name": "Creator Space",
        "description": "desc",
        "task_type": "text",
        "input_types": ["text"],
        "output_types": ["text"],
        "container_image": "img:latest",
        "ui_config": {"inputs": [{"name": "p", "type": "text", "label": "P"}]},
        "runner_config": {},
    }


# ---------------------------------------------------------------------------
# POST /creator/spaces
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_space_returns_201(client):
    response = await client.post("/creator/spaces", json=_space_payload())
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["status"] == "DRAFT"
    assert body["visibility"] == "PRIVATE"


@pytest.mark.asyncio
async def test_create_space_duplicate_slug_returns_409(client):
    payload = _space_payload(slug="dup-slug")
    await client.post("/creator/spaces", json=payload)
    # Second create with same slug for the same owner → 409
    response = await client.post("/creator/spaces", json=payload)
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# GET /creator/spaces
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_my_spaces_empty(client):
    response = await client.get("/creator/spaces")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_my_spaces_returns_own_spaces(client):
    await client.post("/creator/spaces", json=_space_payload())
    await client.post("/creator/spaces", json=_space_payload())
    response = await client.get("/creator/spaces")
    assert response.status_code == 200
    assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# PATCH /creator/spaces/{space_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_space_returns_updated(client):
    create_resp = await client.post("/creator/spaces", json=_space_payload())
    space_id = create_resp.json()["id"]

    response = await client.patch(
        f"/creator/spaces/{space_id}",
        json={"name": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_space_not_found_returns_404(client):
    response = await client.patch(
        f"/creator/spaces/{uuid.uuid4()}",
        json={"name": "X"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_space_not_owner_returns_403(client, db_session):
    """A space owned by a different user cannot be updated by the current creator."""
    unique = uuid.uuid4().hex
    other = User(
        subject_id=f"other-{unique}",
        idp="test",
        email=f"other-{unique}@test.com",
        role="space_creator",
    )
    db_session.add(other)
    await db_session.flush()

    space = Space(
        slug=f"other-{unique}",
        name="Other's Space",
        description="d",
        task_type="t",
        input_types=[],
        output_types=[],
        container_image="img:latest",
        ui_config={},
        runner_config={},
        visibility="PRIVATE",
        status="DRAFT",
        owner_id=other.id,
    )
    db_session.add(space)
    await db_session.commit()

    # dev-user (created by first request) has a different id → 403
    response = await client.patch(
        f"/creator/spaces/{space.public_id}",
        json={"name": "Hacked"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# POST /creator/spaces/{space_id}/validate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_space_valid_config(client):
    payload = _space_payload()
    create_resp = await client.post("/creator/spaces", json=payload)
    space_id = create_resp.json()["id"]

    response = await client.post(f"/creator/spaces/{space_id}/validate")
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["errors"] == []


@pytest.mark.asyncio
async def test_validate_space_invalid_config(client):
    payload = _space_payload()
    payload["ui_config"] = {}  # missing 'inputs' key → validation error
    payload["container_image"] = ""  # empty image → another error
    create_resp = await client.post("/creator/spaces", json=payload)
    space_id = create_resp.json()["id"]

    response = await client.post(f"/creator/spaces/{space_id}/validate")
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert len(body["errors"]) > 0


@pytest.mark.asyncio
async def test_validate_space_not_found_returns_404(client):
    response = await client.post(f"/creator/spaces/{uuid.uuid4()}/validate")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_validate_space_not_owner_returns_403(client, db_session):
    unique = uuid.uuid4().hex
    other = User(
        subject_id=f"other-{unique}",
        idp="test",
        email=f"other-{unique}@test.com",
        role="space_creator",
    )
    db_session.add(other)
    await db_session.flush()

    space = Space(
        slug=f"v-{unique}",
        name="Other",
        description="d",
        task_type="t",
        input_types=[],
        output_types=[],
        container_image="img:latest",
        ui_config={},
        runner_config={},
        visibility="PRIVATE",
        status="DRAFT",
        owner_id=other.id,
    )
    db_session.add(space)
    await db_session.commit()

    response = await client.post(f"/creator/spaces/{space.public_id}/validate")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Role guard: end_user cannot access creator endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_end_user_cannot_access_creator_endpoint(db_session):
    from httpx import ASGITransport, AsyncClient
    from app.core.auth import get_current_user
    from app.db.session import get_db
    from app.main import app

    unique = uuid.uuid4().hex
    end_user = User(
        subject_id=f"eu-{unique}",
        idp="test",
        email=f"eu-{unique}@test.com",
        role="end_user",
    )
    db_session.add(end_user)
    await db_session.flush()

    async def _get_end_user():
        return end_user

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _get_end_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.get("/creator/spaces")

    app.dependency_overrides.clear()
    assert response.status_code == 403
