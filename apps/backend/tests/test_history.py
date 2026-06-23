"""Unit tests for S1-16: user job history and expired artifact cleanup.

Seeds via the ORM so integer primary keys autoincrement. Internal/service calls
use ``.id``; the public history-delete API is addressed by ``.public_id``.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.db.models import Artifact, Job, Space, User
from app.schemas.jobs import JobStatus
from app.services.jobs import delete_job_from_history_service, list_jobs_by_user_service
from app.main import run_cleanup_once


# helpers

async def _seed_user_space_job(db_session, *, expires_at=None, status="SUCCEEDED"):
    """Insert a user, space, and job. Returns the (user, space, job) ORM objects."""
    unique = uuid.uuid4().hex

    user = User(
        subject_id=f"sub-{unique}",
        idp="test",
        email=f"user-{unique}@example.com",
        display_name="Test User",
        role="user",
    )
    db_session.add(user)
    await db_session.flush()

    space = Space(
        slug=f"space-{unique}",
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
    db_session.add(space)
    await db_session.flush()

    job = Job(
        space_id=space.id,
        user_id=user.id,
        status=status,
        input_payload={},
        expires_at=expires_at,
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.commit()
    return user, space, job


async def _seed_artifact(db_session, *, job, expires_at=None):
    """Insert a dummy artifact for a job. Returns the Artifact ORM object."""
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
    db_session.add(artifact)
    await db_session.flush()
    await db_session.commit()
    return artifact


class _NonClosingSession:
    """Wraps the test session so ``async with`` does not close it (the in-memory
    SQLite DB lives on the session's connection and must survive run_cleanup_once)."""

    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc_info):
        return False


# tests

@pytest.mark.asyncio
async def test_history_returns_only_user_jobs(db_session):
    """GET /me/history must return only jobs belonging to the requesting user."""
    user, _, job = await _seed_user_space_job(db_session)
    # seed a second unrelated user + job
    await _seed_user_space_job(db_session)

    jobs = await list_jobs_by_user_service(db_session, user.id)

    assert len(jobs) == 1
    assert jobs[0].id == job.id


@pytest.mark.asyncio
async def test_history_ordered_by_created_at_desc(db_session):
    """Jobs must be returned newest first."""
    unique = uuid.uuid4().hex
    user = User(
        subject_id=f"sub-{unique}",
        idp="test",
        email=f"user-{unique}@example.com",
        display_name="Test User",
        role="user",
    )
    db_session.add(user)
    await db_session.flush()

    space = Space(
        slug=f"space-{unique}",
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
    db_session.add(space)
    await db_session.flush()

    for _ in range(3):
        db_session.add(
            Job(space_id=space.id, user_id=user.id, status="SUCCEEDED", input_payload={})
        )
    await db_session.commit()

    jobs = await list_jobs_by_user_service(db_session, user.id)

    assert len(jobs) == 3
    assert jobs[0].created_at >= jobs[1].created_at >= jobs[2].created_at


@pytest.mark.asyncio
async def test_delete_job_removes_it(db_session):
    """DELETE /me/history/{job_id} must remove the job from the DB."""
    user, _, job = await _seed_user_space_job(db_session)

    await delete_job_from_history_service(db_session, job.public_id, user.id)

    result = await db_session.execute(select(Job).where(Job.id == job.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_job_wrong_user_raises_403(db_session):
    """DELETE by a different user must raise 403."""
    from fastapi import HTTPException

    user, _, job = await _seed_user_space_job(db_session)
    other_user_id = user.id + 1000

    with pytest.raises(HTTPException) as exc_info:
        await delete_job_from_history_service(db_session, job.public_id, other_user_id)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_job_not_found_raises_404(db_session):
    """DELETE on a non-existent job must raise 404."""
    from fastapi import HTTPException

    non_existent_public_id = uuid.uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await delete_job_from_history_service(db_session, non_existent_public_id, 999999)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_job_also_removes_artifacts(db_session):
    """Deleting a job must also delete its artifacts."""
    user, _, job = await _seed_user_space_job(db_session)
    artifact = await _seed_artifact(db_session, job=job)

    await delete_job_from_history_service(db_session, job.public_id, user.id)

    result = await db_session.execute(select(Artifact).where(Artifact.id == artifact.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_job_also_removes_files(db_session, monkeypatch):
    """Deleting from history must remove the artifact files and job dir from disk (C2)."""
    deleted_files: list[str] = []
    deleted_job_dirs: list = []
    monkeypatch.setattr(
        "app.services.jobs.delete_storage_file",
        lambda path: deleted_files.append(path),
    )
    monkeypatch.setattr(
        "app.services.jobs.delete_job_storage",
        lambda job_id: deleted_job_dirs.append(job_id),
    )

    user, _, job = await _seed_user_space_job(db_session)
    artifact = await _seed_artifact(db_session, job=job)
    storage_path = artifact.storage_path
    job_id = job.id

    await delete_job_from_history_service(db_session, job.public_id, user.id)

    # DB rows gone...
    assert (
        await db_session.execute(select(Job).where(Job.id == job_id))
    ).scalar_one_or_none() is None
    assert (
        await db_session.execute(select(Artifact).where(Artifact.job_id == job_id))
    ).scalars().all() == []
    # ...and the storage helpers were called for the files and the job dir.
    assert storage_path in deleted_files
    assert job_id in deleted_job_dirs


@pytest.mark.asyncio
async def test_cleanup_expires_jobs_and_removes_artifacts(db_session, monkeypatch):
    """Cleanup marks expired jobs as EXPIRED (D3) and removes their artifact rows."""
    past = datetime.now(timezone.utc) - timedelta(days=1)
    _, _, job = await _seed_user_space_job(db_session, expires_at=past)
    artifact = await _seed_artifact(db_session, job=job, expires_at=past)

    # Point cleanup at the test DB session without closing it on exit.
    monkeypatch.setattr(
        "app.main.AsyncSessionLocal",
        lambda: _NonClosingSession(db_session),
    )

    await run_cleanup_once()

    art = await db_session.execute(select(Artifact).where(Artifact.id == artifact.id))
    assert art.scalar_one_or_none() is None

    refreshed = await db_session.execute(select(Job).where(Job.id == job.id))
    expired_job = refreshed.scalar_one_or_none()
    assert expired_job is not None
    assert expired_job.status == JobStatus.EXPIRED.value


@pytest.mark.asyncio
async def test_cleanup_keeps_non_expired(db_session, monkeypatch):
    """Cleanup must NOT touch jobs/artifacts that are still valid."""
    future = datetime.now(timezone.utc) + timedelta(days=10)
    _, _, job = await _seed_user_space_job(db_session, expires_at=future)
    artifact = await _seed_artifact(db_session, job=job, expires_at=future)

    monkeypatch.setattr(
        "app.main.AsyncSessionLocal",
        lambda: _NonClosingSession(db_session),
    )

    await run_cleanup_once()

    art = await db_session.execute(select(Artifact).where(Artifact.id == artifact.id))
    assert art.scalar_one_or_none() is not None

    refreshed = await db_session.execute(select(Job).where(Job.id == job.id))
    kept_job = refreshed.scalar_one_or_none()
    assert kept_job is not None
    assert kept_job.status != JobStatus.EXPIRED.value
