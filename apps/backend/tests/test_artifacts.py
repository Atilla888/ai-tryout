"""Integration tests for artifact upload, preview, download, and listing.

Uploads happen on the internal API (integer job id); preview/download/list are
public (UUID artifact/job public_id), so the tests bridge an artifact's integer
id to its public_id via the DB where needed.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.db.models import Artifact


async def _artifact_public_id(db, artifact_db_id):
    """Look up a freshly-uploaded artifact's public UUID by its integer id."""
    return (
        await db.execute(select(Artifact.public_id).where(Artifact.id == artifact_db_id))
    ).scalar_one()


@pytest.mark.asyncio
async def test_upload_and_preview_artifact(client, db_session, seed_job):
    job = seed_job
    file_content = b"hello artifact"

    response = await client.post(
        f"/internal/jobs/{job.id}/artifacts",
        data={"artifact_type": "text", "preview_supported": "true"},
        files={"file": ("hello.txt", file_content, "text/plain")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["job_id"] == job.id
    assert body["artifact_type"] == "text"
    assert body["file_name"] == "hello.txt"
    assert body["size_bytes"] == len(file_content)
    assert body["preview_supported"] is True
    assert body["expires_at"] is not None

    public_id = await _artifact_public_id(db_session, body["id"])
    preview = await client.get(f"/artifacts/{public_id}/preview")
    assert preview.status_code == 200
    assert preview.content == file_content
    assert preview.headers["content-type"].startswith("text/plain")


@pytest.mark.asyncio
async def test_upload_and_download_artifact(client, db_session, seed_job):
    job = seed_job
    file_content = b"download me"

    response = await client.post(
        f"/internal/jobs/{job.id}/artifacts",
        data={"artifact_type": "file"},
        files={"file": ("data.bin", file_content, "application/octet-stream")},
    )
    assert response.status_code == 201
    public_id = await _artifact_public_id(db_session, response.json()["id"])

    download = await client.get(f"/artifacts/{public_id}/download")
    assert download.status_code == 200
    assert download.content == file_content
    assert "attachment" in download.headers.get("content-disposition", "").lower()


@pytest.mark.asyncio
async def test_list_job_artifacts(client, seed_job):
    job = seed_job

    for index in range(2):
        await client.post(
            f"/internal/jobs/{job.id}/artifacts",
            data={"artifact_type": "image"},
            files={"file": (f"img{index}.png", b"\x89PNG", "image/png")},
        )

    response = await client.get(f"/jobs/{job.public_id}/artifacts")
    assert response.status_code == 200
    artifacts = response.json()
    assert len(artifacts) == 2
    assert all(item["job_id"] == str(job.public_id) for item in artifacts)


@pytest.mark.asyncio
async def test_upload_artifact_unknown_job(client):
    response = await client.post(
        "/internal/jobs/999999/artifacts",
        data={"artifact_type": "text"},
        files={"file": ("x.txt", b"x", "text/plain")},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_expired_artifact_not_previewable(client, db_session, seed_job):
    job = seed_job

    upload = await client.post(
        f"/internal/jobs/{job.id}/artifacts",
        data={"artifact_type": "text"},
        files={"file": ("expired.txt", b"gone", "text/plain")},
    )
    assert upload.status_code == 201
    artifact_db_id = upload.json()["id"]

    await db_session.execute(
        update(Artifact)
        .where(Artifact.id == artifact_db_id)
        .values(expires_at=datetime.now(timezone.utc) - timedelta(days=1))
    )
    await db_session.commit()

    public_id = await _artifact_public_id(db_session, artifact_db_id)
    preview = await client.get(f"/artifacts/{public_id}/preview")
    assert preview.status_code == 404
