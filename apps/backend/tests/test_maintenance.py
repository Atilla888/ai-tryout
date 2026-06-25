"""Unit tests for cleanup_expired_jobs_and_artifacts (retention lifecycle, D3).

Covers both loops of the cleanup pass: expired jobs (status -> EXPIRED, artifact
rows + files removed) and the orphan-artifact safety net. Uses the in-memory
test DB from conftest.py and spies on the storage delete helpers via monkeypatch.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.db.models import Artifact, Job, Space, User
from app.schemas.jobs import JobStatus
from app.services.maintenance import cleanup_expired_jobs_and_artifacts


PAST = datetime.now(timezone.utc) - timedelta(days=1)
FUTURE = datetime.now(timezone.utc) + timedelta(days=10)


# helpers — seed via ORM so integer primary keys autoincrement

async def _make_space(db):
    """Insert an owner user and a published space; return the Space."""
    user = User(
        subject_id=f"sub-{datetime.now(timezone.utc).timestamp()}",
        idp="test",
        email=f"user-{datetime.now(timezone.utc).timestamp()}@example.com",
        display_name="Owner",
        role="user",
    )
    db.add(user)
    await db.flush()

    space = Space(
        slug=f"space-{user.id}",
        name="Test Space",
        description="desc",
        task_type="demo",
        input_types=[],
        output_types=[],
        container_image="img:latest",
        ui_config={},
        runner_config={},
        visibility="PUBLIC",
        status="PUBLISHED",
        owner_id=user.id,
    )
    db.add(space)
    await db.flush()
    return space


async def _make_job(db, space, *, status="SUCCEEDED", expires_at=None):
    job = Job(
        space_id=space.id,
        user_id=space.owner_id,
        status=status,
        input_payload={},
        expires_at=expires_at,
    )
    db.add(job)
    await db.flush()
    return job


async def _make_artifact(db, job, *, expires_at=None):
    artifact = Artifact(
        job_id=job.id,
        artifact_type="OUTPUT",
        file_name="result.png",
        content_type="image/png",
        size_bytes=1234,
        storage_path=f"jobs/{job.id}/output/result.png",
        preview_supported=True,
        expires_at=expires_at,
    )
    db.add(artifact)
    await db.flush()
    return artifact


@pytest.fixture
def storage_spy(monkeypatch):
    """Record calls to the storage delete helpers instead of touching disk."""
    calls = {"files": [], "jobs": []}
    monkeypatch.setattr(
        "app.services.maintenance.delete_storage_file",
        lambda path: calls["files"].append(path),
    )
    monkeypatch.setattr(
        "app.services.maintenance.delete_job_storage",
        lambda job_id: calls["jobs"].append(job_id),
    )
    return calls


# tests

@pytest.mark.asyncio
async def test_expired_job_is_marked_expired_and_artifacts_removed(db_session, storage_spy):
    from sqlalchemy import select

    space = await _make_space(db_session)
    job = await _make_job(db_session, space, expires_at=PAST)
    artifact = await _make_artifact(db_session, job)
    await db_session.commit()
    storage_path = artifact.storage_path

    result = await cleanup_expired_jobs_and_artifacts(db_session)

    assert result.jobs_expired == 1
    assert result.artifacts_removed == 1

    refreshed = (await db_session.execute(select(Job).where(Job.id == job.id))).scalar_one()
    assert refreshed.status == JobStatus.EXPIRED.value

    remaining = (
        await db_session.execute(select(Artifact).where(Artifact.job_id == job.id))
    ).scalars().all()
    assert remaining == []

    assert storage_path in storage_spy["files"]
    assert job.id in storage_spy["jobs"]


@pytest.mark.asyncio
async def test_non_expired_job_is_left_untouched(db_session, storage_spy):
    from sqlalchemy import select

    space = await _make_space(db_session)
    job = await _make_job(db_session, space, status="RUNNING", expires_at=FUTURE)
    artifact = await _make_artifact(db_session, job, expires_at=FUTURE)
    await db_session.commit()

    result = await cleanup_expired_jobs_and_artifacts(db_session)

    assert result.jobs_expired == 0
    assert result.artifacts_removed == 0

    refreshed = (await db_session.execute(select(Job).where(Job.id == job.id))).scalar_one()
    assert refreshed.status == "RUNNING"

    still_there = (
        await db_session.execute(select(Artifact).where(Artifact.id == artifact.id))
    ).scalar_one_or_none()
    assert still_there is not None

    assert storage_spy["files"] == []
    assert storage_spy["jobs"] == []


@pytest.mark.asyncio
async def test_orphan_artifact_is_removed_even_if_job_not_expired(db_session, storage_spy):
    from sqlalchemy import select

    space = await _make_space(db_session)
    # Job itself is still within its retention window...
    job = await _make_job(db_session, space, status="RUNNING", expires_at=FUTURE)
    # ...but this artifact has its own, already-passed expiry.
    artifact = await _make_artifact(db_session, job, expires_at=PAST)
    await db_session.commit()
    storage_path = artifact.storage_path

    result = await cleanup_expired_jobs_and_artifacts(db_session)

    assert result.jobs_expired == 0
    assert result.artifacts_removed == 1

    refreshed = (await db_session.execute(select(Job).where(Job.id == job.id))).scalar_one()
    assert refreshed.status == "RUNNING"

    gone = (
        await db_session.execute(select(Artifact).where(Artifact.id == artifact.id))
    ).scalar_one_or_none()
    assert gone is None

    assert storage_path in storage_spy["files"]
    # The whole-job directory is only removed when a job expires, not for orphans.
    assert storage_spy["jobs"] == []


@pytest.mark.asyncio
async def test_empty_database_returns_zero_counts(db_session, storage_spy):
    result = await cleanup_expired_jobs_and_artifacts(db_session)

    assert result.jobs_expired == 0
    assert result.artifacts_removed == 0
    assert storage_spy["files"] == []
    assert storage_spy["jobs"] == []
