"""Integration tests for the public spaces API (router/spaces.py)."""

import uuid

import pytest

from app.db.models import Space, User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_space(
    db_session,
    *,
    visibility="PUBLIC",
    status="PUBLISHED",
    slug=None,
) -> Space:
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
        slug=slug or f"s-{unique}",
        name="Test Space",
        description="desc",
        task_type="text",
        input_types=["text"],
        output_types=["text"],
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


# ---------------------------------------------------------------------------
# GET /spaces — public catalog
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_spaces_empty(client):
    response = await client.get("/spaces")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_spaces_only_published_public(client, db_session):
    """Only PUBLISHED + PUBLIC spaces should appear in the public catalog."""
    await _seed_space(db_session, visibility="PUBLIC", status="PUBLISHED")
    await _seed_space(db_session, visibility="PRIVATE", status="PUBLISHED")
    await _seed_space(db_session, visibility="PUBLIC", status="DRAFT")

    response = await client.get("/spaces")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["visibility"] == "PUBLIC"
    assert data[0]["status"] == "PUBLISHED"


@pytest.mark.asyncio
async def test_list_spaces_returns_multiple(client, db_session):
    await _seed_space(db_session)
    await _seed_space(db_session)
    response = await client.get("/spaces")
    assert response.status_code == 200
    assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# GET /spaces/{space_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_space_by_id_returns_space(client, db_session):
    space = await _seed_space(db_session)
    response = await client.get(f"/spaces/{space.public_id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(space.public_id)


@pytest.mark.asyncio
async def test_get_space_by_id_not_found_returns_404(client):
    response = await client.get(f"/spaces/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_space_also_returns_private_spaces_by_id(client, db_session):
    """The single-lookup endpoint does not filter by visibility."""
    space = await _seed_space(db_session, visibility="PRIVATE", status="DRAFT")
    response = await client.get(f"/spaces/{space.public_id}")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /spaces — requires space_creator or admin role
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_space_as_creator_returns_201(client):
    payload = {
        "slug": f"new-{uuid.uuid4().hex[:8]}",
        "name": "New Space",
        "description": "d",
        "task_type": "text",
        "input_types": ["text"],
        "output_types": ["text"],
        "container_image": "img:latest",
        "ui_config": {},
        "runner_config": {},
    }
    # DevAuthProvider injects admin role, which satisfies space_creator|admin
    response = await client.post("/spaces", json=payload)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_space_duplicate_slug_returns_409(client):
    slug = f"dup-{uuid.uuid4().hex[:8]}"
    payload = {
        "slug": slug,
        "name": "D",
        "description": "d",
        "task_type": "text",
        "input_types": [],
        "output_types": [],
        "container_image": "img:latest",
        "ui_config": {},
        "runner_config": {},
    }
    await client.post("/spaces", json=payload)
    response = await client.post("/spaces", json=payload)
    assert response.status_code == 409
