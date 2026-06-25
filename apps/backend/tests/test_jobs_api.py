"""Integration tests for the public jobs API (router/jobs.py).

Tests cover: submit, get, list artifacts, cancel (all branches).
"""

import uuid

import pytest

from app.db.models import Job, Space, User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_space(db_session) -> Space:
    """Insert a minimal published+public Space and its owner. Returns the Space."""
    unique = uuid.uuid4().hex
    owner = User(
        subject_id=f"owner-{unique}",
        idp="test",
        email=f"owner-{unique}@test.com",
        display_name="Owner",
        role="space_creator",
    )
    db_session.add(owner)
    await db_session.flush()

    space = Space(
        slug=f"s-{unique}",
        name="Test Space",
        description="desc",
        task_type="text",
        input_types=["text"],
        output_types=["text"],
        container_image="img:latest",
        ui_config={"inputs": [{"name": "prompt", "type": "text", "label": "Prompt"}]},
        runner_config={},
        visibility="PUBLIC",
        status="PUBLISHED",
        owner_id=owner.id,
    )
    db_session.add(space)
    await db_session.commit()
    return space


# ---------------------------------------------------------------------------
# POST /spaces/{space_id}/jobs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_job_returns_queued(client, db_session):
    space = await _seed_space(db_session)
    response = await client.post(
        f"/spaces/{space.public_id}/jobs",
        data={"prompt": "hello"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "QUEUED"
    assert body["queue_position"] == 1
    assert "id" in body


@pytest.mark.asyncio
async def test_create_job_unknown_space_returns_404(client):
    response = await client.post(
        f"/spaces/{uuid.uuid4()}/jobs",
        data={"prompt": "hello"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_job_empty_form_returns_400(client, db_session):
    space = await _seed_space(db_session)
    # send a form with no fields at all
    response = await client.post(
        f"/spaces/{space.public_id}/jobs",
        data={},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_job_by_public_id(client, db_session):
    space = await _seed_space(db_session)
    create_resp = await client.post(
        f"/spaces/{space.public_id}/jobs",
        data={"prompt": "world"},
    )
    job_id = create_resp.json()["id"]

    response = await client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["id"] == job_id
    assert response.json()["status"] == "QUEUED"


@pytest.mark.asyncio
async def test_get_job_not_found_returns_404(client):
    response = await client.get(f"/jobs/{uuid.uuid4()}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/artifacts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_job_artifacts_empty(client, db_session):
    space = await _seed_space(db_session)
    create_resp = await client.post(
        f"/spaces/{space.public_id}/jobs",
        data={"prompt": "x"},
    )
    job_id = create_resp.json()["id"]

    response = await client.get(f"/jobs/{job_id}/artifacts")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_job_artifacts_not_found_returns_404(client):
    response = await client.get(f"/jobs/{uuid.uuid4()}/artifacts")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_job_artifacts_includes_outputs(client, db_session, seed_job):
    """Upload an output artifact then confirm it appears in the public listing."""
    job = seed_job
    await client.post(
        f"/internal/jobs/{job.id}/artifacts",
        data={"artifact_type": "text"},
        files={"file": ("out.txt", b"result", "text/plain")},
    )
    response = await client.get(f"/jobs/{job.public_id}/artifacts")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["job_id"] == str(job.public_id)


# ---------------------------------------------------------------------------
# POST /jobs/{job_id}/cancel
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancel_queued_job_returns_cancelled(client, db_session):
    space = await _seed_space(db_session)
    create_resp = await client.post(
        f"/spaces/{space.public_id}/jobs",
        data={"prompt": "cancel me"},
    )
    job_id = create_resp.json()["id"]

    response = await client.post(f"/jobs/{job_id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_cancel_running_job_returns_cancelling(client, db_session):
    """A RUNNING job transitions to CANCELLING when cancelled via the API."""
    space = await _seed_space(db_session)
    create_resp = await client.post(
        f"/spaces/{space.public_id}/jobs",
        data={"prompt": "run"},
    )
    job_id = create_resp.json()["id"]

    # Advance to RUNNING via internal endpoints
    job_obj = await db_session.get(
        Job,
        (await client.get("/internal/jobs?status=QUEUED")).json()[0]["id"],
    )
    await client.patch(f"/internal/jobs/{job_obj.id}/start")
    await client.patch(
        f"/internal/jobs/{job_obj.id}/progress",
        json={"progress_percent": 10, "progress_message": "working"},
    )

    response = await client.post(f"/jobs/{job_id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLING"


@pytest.mark.asyncio
async def test_cancel_succeeded_job_returns_409(client, db_session):
    """Cancelling a terminal job is rejected with 409."""
    space = await _seed_space(db_session)
    create_resp = await client.post(
        f"/spaces/{space.public_id}/jobs",
        data={"prompt": "done"},
    )
    job_id = create_resp.json()["id"]

    # Advance to SUCCEEDED
    int_jobs = (await client.get("/internal/jobs?status=QUEUED")).json()
    int_id = int_jobs[0]["id"]
    await client.patch(f"/internal/jobs/{int_id}/start")
    await client.patch(
        f"/internal/jobs/{int_id}/progress",
        json={"progress_percent": 100, "progress_message": "done"},
    )
    await client.patch(f"/internal/jobs/{int_id}/succeed")

    response = await client.post(f"/jobs/{job_id}/cancel")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_cancel_job_not_found_returns_404(client):
    response = await client.post(f"/jobs/{uuid.uuid4()}/cancel")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_job_not_owner_returns_403(db_session):
    """An end_user cannot cancel a job they do not own."""
    from httpx import ASGITransport, AsyncClient
    from app.core.auth import get_current_user
    from app.db.session import get_db
    from app.main import app

    # Seed a job owned by a specific user
    unique = uuid.uuid4().hex
    owner = User(
        subject_id=f"owner-{unique}",
        idp="test",
        email=f"owner-{unique}@test.com",
        role="end_user",
    )
    db_session.add(owner)
    await db_session.flush()

    space = Space(
        slug=f"sp-{unique}", name="S", description="d", task_type="t",
        input_types=[], output_types=[], container_image="img:latest",
        ui_config={}, runner_config={}, visibility="PUBLIC",
        status="PUBLISHED", owner_id=owner.id,
    )
    db_session.add(space)
    await db_session.flush()

    job = Job(space_id=space.id, user_id=owner.id, status="QUEUED", input_payload={})
    db_session.add(job)
    await db_session.commit()

    # A different end_user tries to cancel it
    different = User(
        subject_id=f"other-{unique}",
        idp="test",
        email=f"other-{unique}@test.com",
        role="end_user",
    )
    db_session.add(different)
    await db_session.flush()

    async def _get_different_user():
        return different

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _get_different_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.post(f"/jobs/{job.public_id}/cancel")

    app.dependency_overrides.clear()
    assert response.status_code == 403
