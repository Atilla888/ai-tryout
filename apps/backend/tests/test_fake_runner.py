"""Integration test matching fake_runner.py behaviour against the API."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.test_job_transitions import _seed_space_and_user

TEST_TOKEN = "test-internal-token"


@pytest.fixture
async def api_client(db_session, configure_test_settings, monkeypatch):
    monkeypatch.setattr("app.config.settings.internal_service_token", TEST_TOKEN)

    from app.db import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Service-Token": TEST_TOKEN},
    ) as client:
        yield client
    app.dependency_overrides.clear()


async def _create_started_job(client: AsyncClient, db_session) -> str:
    """Submits and starts a job via the API. Returns the job_id string."""
    user_id, space_id = await _seed_space_and_user(db_session)
    created = await client.post(f"/spaces/{space_id}/jobs", data={"prompt": "fake run"})
    assert created.status_code == 201
    job_id = created.json()["id"]
    started = await client.patch(f"/internal/jobs/{job_id}/start")
    assert started.status_code == 200
    return job_id


@pytest.mark.asyncio
async def test_fake_runner_happy_path(api_client, db_session):
    job_id = await _create_started_job(api_client, db_session)

    for percent in (20, 40, 60, 80):
        progress = await api_client.patch(
            f"/internal/jobs/{job_id}/progress",
            json={"progress_percent": percent, "message": f"Processing… {percent}%"},
        )
        assert progress.status_code == 200

    upload = await api_client.post(
        f"/internal/jobs/{job_id}/artifacts",
        data={"artifact_type": "text", "preview_supported": "true"},
        files={"file": ("result.txt", b"AI Spaces fake runner output\n", "text/plain")},
    )
    assert upload.status_code == 201
    artifact_id = upload.json()["id"]

    done = await api_client.patch(f"/internal/jobs/{job_id}/succeed")
    assert done.status_code == 200
    assert done.json()["status"] == "SUCCEEDED"

    preview = await api_client.get(f"/artifacts/{artifact_id}/preview")
    assert preview.status_code == 200
    assert b"fake runner" in preview.content


@pytest.mark.asyncio
async def test_fake_runner_simulate_failure(api_client, db_session):
    job_id = await _create_started_job(api_client, db_session)
    failed = await api_client.patch(
        f"/internal/jobs/{job_id}/fail",
        json={"error_code": "SIMULATED_FAILURE", "error_message": "Fake runner simulated failure"},
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "FAILED"
