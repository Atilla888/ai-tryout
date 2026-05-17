"""Integration test: upload artifact via internal endpoint, retrieve via preview."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import insert

from app.models import ArtifactType, Job, JobStatus, Space, SpaceStatus, SpaceVisibility, User, UserRole


@pytest_asyncio.fixture
async def seed_job(db_session, tmp_path):
    """Insert a minimal user, space, and job into the test DB."""
    user_id = uuid.uuid4()
    space_id = uuid.uuid4()
    job_id = uuid.uuid4()

    await db_session.execute(
        insert(User).values(id=user_id, display_name="Test", email="test@example.com", role=UserRole.user)
    )
    await db_session.execute(
        insert(Space).values(
            id=space_id,
            name="Test Space",
            slug="test-space",
            task_type="text-to-image",
            owner_id=user_id,
            visibility=SpaceVisibility.public,
            status=SpaceStatus.published,
        )
    )
    await db_session.execute(
        insert(Job).values(
            id=job_id,
            space_id=space_id,
            user_id=user_id,
            status=JobStatus.running,
        )
    )
    await db_session.commit()
    return job_id


@pytest.mark.asyncio
async def test_upload_and_preview_artifact(client, seed_job, tmp_path):
    job_id = seed_job
    file_content = b"hello artifact"

    # Upload
    response = await client.post(
        f"/internal/jobs/{job_id}/artifacts",
        data={"artifact_type": ArtifactType.text.value, "preview_supported": "true"},
        files={"file": ("hello.txt", file_content, "text/plain")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["job_id"] == str(job_id)
    assert body["artifact_type"] == "text"
    assert body["file_name"] == "hello.txt"
    assert body["size_bytes"] == len(file_content)
    assert body["preview_supported"] is True
    assert body["expires_at"] is not None

    artifact_id = body["id"]

    # Preview
    preview = await client.get(f"/artifacts/{artifact_id}/preview")
    assert preview.status_code == 200
    assert preview.content == file_content
    assert preview.headers["content-type"].startswith("text/plain")


@pytest.mark.asyncio
async def test_upload_and_download_artifact(client, seed_job):
    job_id = seed_job
    file_content = b"download me"

    response = await client.post(
        f"/internal/jobs/{job_id}/artifacts",
        data={"artifact_type": ArtifactType.file.value},
        files={"file": ("data.bin", file_content, "application/octet-stream")},
    )
    assert response.status_code == 201
    artifact_id = response.json()["id"]

    download = await client.get(f"/artifacts/{artifact_id}/download")
    assert download.status_code == 200
    assert download.content == file_content
    assert "attachment" in download.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_list_job_artifacts(client, seed_job):
    job_id = seed_job

    # Upload two artifacts
    for i in range(2):
        await client.post(
            f"/internal/jobs/{job_id}/artifacts",
            data={"artifact_type": ArtifactType.image.value},
            files={"file": (f"img{i}.png", b"\x89PNG", "image/png")},
        )

    response = await client.get(f"/jobs/{job_id}/artifacts")
    assert response.status_code == 200
    # at least the two we just uploaded (fixture may have run other tests before)
    assert len(response.json()) >= 2


@pytest.mark.asyncio
async def test_upload_artifact_unknown_job(client):
    response = await client.post(
        f"/internal/jobs/{uuid.uuid4()}/artifacts",
        data={"artifact_type": ArtifactType.text.value},
        files={"file": ("x.txt", b"x", "text/plain")},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_preview_unknown_artifact(client):
    response = await client.get(f"/artifacts/{uuid.uuid4()}/preview")
    assert response.status_code == 404
