"""Unit tests for S1-16: user job history and expired artifact cleanup."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import insert, select

from app.db.models import Artifact, Job, Space, User
from app.services.jobs import delete_job_from_history_service, list_jobs_by_user_service
from app.main import cleanup_expired_artifacts


# helpers 

async def _seed_user_space_job(db_session, *, expires_at=None, status="SUCCEEDED"):
    """Insert a user, space, and job. Returns (user_id, space_id, job_id)."""
    user_id = uuid.uuid7()
    space_id = uuid.uuid7()
    job_id = uuid.uuid7()
    unique = uuid.uuid7().hex

    await db_session.execute(
        insert(User).values(
            id=user_id,
            subject_id=f"sub-{unique}",
            idp="test",
            email=f"user-{unique}@example.com",
            display_name="Test User",
            role="user",
        )
    )
    await db_session.execute(
        insert(Space).values(
            id=space_id,
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
            owner_id=user_id,
        )
    )
    await db_session.execute(
        insert(Job).values(
            id=job_id,
            space_id=space_id,
            user_id=user_id,
            status=status,
            input_payload={},
            expires_at=expires_at,
        )
    )
    await db_session.commit()
    return user_id, space_id, job_id


async def _seed_artifact(db_session, *, job_id, expires_at=None):
    """Insert a dummy artifact for a job."""
    artifact_id = uuid.uuid7()
    await db_session.execute(
        insert(Artifact).values(
            id=artifact_id,
            job_id=job_id,
            artifact_type="OUTPUT",
            file_name="result.png",
            content_type="image/png",
            size_bytes=1234,
            storage_path=f"storage/{job_id}/result.png",
            preview_supported=True,
            expires_at=expires_at,
        )
    )
    await db_session.commit()
    return artifact_id


# tests

@pytest.mark.asyncio
async def test_history_returns_only_user_jobs(db_session):
    """GET /me/history must return only jobs belonging to the requesting user."""
    user_id, _, job_id = await _seed_user_space_job(db_session)
    # seed a second unrelated user + job
    await _seed_user_space_job(db_session)

    jobs = await list_jobs_by_user_service(db_session, user_id)

    assert len(jobs) == 1
    assert jobs[0].id == job_id


@pytest.mark.asyncio
async def test_history_ordered_by_created_at_desc(db_session):
    """Jobs must be returned newest first."""
    user_id = uuid.uuid7()
    space_id = uuid.uuid7()
    unique = uuid.uuid7().hex

    await db_session.execute(
        insert(User).values(
            id=user_id,
            subject_id=f"sub-{unique}",
            idp="test",
            email=f"user-{unique}@example.com",
            display_name="Test User",
            role="user",
        )
    )
    await db_session.execute(
        insert(Space).values(
            id=space_id,
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
            owner_id=user_id,
        )
    )

    job_ids = []
    for _ in range(3):
        job_id = uuid.uuid7()
        job_ids.append(job_id)
        await db_session.execute(
            insert(Job).values(
                id=job_id,
                space_id=space_id,
                user_id=user_id,
                status="SUCCEEDED",
                input_payload={},
            )
        )
    await db_session.commit()

    jobs = await list_jobs_by_user_service(db_session, user_id)

    assert len(jobs) == 3
    assert jobs[0].created_at >= jobs[1].created_at >= jobs[2].created_at


@pytest.mark.asyncio
async def test_delete_job_removes_it(db_session):
    """DELETE /me/history/{job_id} must remove the job from the DB."""
    user_id, _, job_id = await _seed_user_space_job(db_session)

    await delete_job_from_history_service(db_session, job_id, user_id)

    result = await db_session.execute(select(Job).where(Job.id == job_id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_job_wrong_user_raises_403(db_session):
    """DELETE by a different user must raise 403."""
    from fastapi import HTTPException

    user_id, _, job_id = await _seed_user_space_job(db_session)
    other_user_id = uuid.uuid7()

    with pytest.raises(HTTPException) as exc_info:
        await delete_job_from_history_service(db_session, job_id, other_user_id)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_job_not_found_raises_404(db_session):
    """DELETE on a non-existent job must raise 404."""
    from fastapi import HTTPException

    non_existent_id = uuid.uuid7()
    user_id = uuid.uuid7()

    with pytest.raises(HTTPException) as exc_info:
        await delete_job_from_history_service(db_session, non_existent_id, user_id)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_job_also_removes_artifacts(db_session):
    """Deleting a job must also delete its artifacts."""
    user_id, _, job_id = await _seed_user_space_job(db_session)
    artifact_id = await _seed_artifact(db_session, job_id=job_id)

    await delete_job_from_history_service(db_session, job_id, user_id)

    result = await db_session.execute(select(Artifact).where(Artifact.id == artifact_id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_cleanup_removes_expired_artifacts(db_session, monkeypatch):
    """Cleanup task must delete artifacts and jobs where expires_at has passed."""
    from app.db import AsyncSessionLocal

    past = datetime.now(timezone.utc) - timedelta(days=1)
    user_id, _, job_id = await _seed_user_space_job(db_session, expires_at=past)
    artifact_id = await _seed_artifact(db_session, job_id=job_id, expires_at=past)

    # Point cleanup at the test DB session
    monkeypatch.setattr(
        "app.main.AsyncSessionLocal",
        lambda: db_session,
    )

    await cleanup_expired_artifacts()

    art = await db_session.execute(select(Artifact).where(Artifact.id == artifact_id))
    assert art.scalar_one_or_none() is None

    job = await db_session.execute(select(Job).where(Job.id == job_id))
    assert job.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_cleanup_keeps_non_expired(db_session, monkeypatch):
    """Cleanup task must NOT delete artifacts that are still valid."""
    future = datetime.now(timezone.utc) + timedelta(days=10)
    user_id, _, job_id = await _seed_user_space_job(db_session, expires_at=future)
    artifact_id = await _seed_artifact(db_session, job_id=job_id, expires_at=future)

    monkeypatch.setattr(
        "app.main.AsyncSessionLocal",
        lambda: db_session,
    )

    await cleanup_expired_artifacts()

    art = await db_session.execute(select(Artifact).where(Artifact.id == artifact_id))
    assert art.scalar_one_or_none() is not None
