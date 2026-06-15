"""Unit tests for job lifecycle transitions and queue positions."""

import uuid

import pytest
from sqlalchemy import insert, select

from app.db.models import Job, Space, User
from app.schemas.jobs import JobStatus
from app.services.job_transitions import JobTransitionError, ensure_transition
from app.services.jobs import (
    cancel_job_service,
    create_job_service,
    fail_job_service,
    list_jobs_by_status_service,
    recalculate_queue_positions,
    start_job_service,
    succeed_job_service,
    update_job_progress_service,
)


async def _seed_space_and_user(db_session):
    """Inserts a User and a published Space into the test DB. Returns (user_id, space_id)."""
    user_id = uuid.uuid7()
    space_id = uuid.uuid7()
    unique = uuid.uuid7().hex
    await db_session.execute(
        insert(User).values(
            id=user_id,
            subject_id=f"sub-{unique}",
            idp="test",
            email=f"user-{unique}@example.com",
            display_name="Test",
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
    await db_session.commit()
    return user_id, space_id


@pytest.mark.asyncio
async def test_create_job_assigns_queue_position(db_session):
    user_id, space_id = await _seed_space_and_user(db_session)
    first = await create_job_service(db_session, space_id, user_id, {"prompt": "a"}, {})
    second = await create_job_service(db_session, space_id, user_id, {"prompt": "b"}, {})
    assert first.queue_position == 1
    assert second.queue_position == 2
    assert first.status == JobStatus.QUEUED
    assert second.status == JobStatus.QUEUED


@pytest.mark.asyncio
async def test_queue_recalculates_when_first_job_starts(db_session):
    user_id, space_id = await _seed_space_and_user(db_session)
    first = await create_job_service(db_session, space_id, user_id, {"a": "1"}, {})
    second = await create_job_service(db_session, space_id, user_id, {"b": "2"}, {})
    job1 = await db_session.get(Job, first.id)
    await start_job_service(db_session, job1)
    job2 = await db_session.get(Job, second.id)
    assert job2.queue_position == 1


@pytest.mark.asyncio
async def test_queued_job_cancel_is_immediate(db_session):
    user_id, space_id = await _seed_space_and_user(db_session)
    created = await create_job_service(db_session, space_id, user_id, {}, {})
    job = await db_session.get(Job, created.id)
    cancelled = await cancel_job_service(db_session, job)
    assert cancelled.status == JobStatus.CANCELLED.value
    assert cancelled.cancelled_at is not None
    assert cancelled.queue_position is None


@pytest.mark.asyncio
async def test_running_job_cancel_goes_through_cancelling(db_session):
    user_id, space_id = await _seed_space_and_user(db_session)
    created = await create_job_service(db_session, space_id, user_id, {}, {})
    job = await db_session.get(Job, created.id)
    await start_job_service(db_session, job)
    await db_session.refresh(job)
    await update_job_progress_service(db_session, job, progress_percent=10, message="working")
    cancelled = await cancel_job_service(db_session, job)
    assert cancelled.status == JobStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_happy_path_start_progress_succeed(db_session):
    user_id, space_id = await _seed_space_and_user(db_session)
    created = await create_job_service(db_session, space_id, user_id, {}, {})
    job = await db_session.get(Job, created.id)
    await start_job_service(db_session, job)
    await db_session.refresh(job)
    await update_job_progress_service(db_session, job, progress_percent=50, message="half")
    assert job.status == JobStatus.RUNNING.value
    done = await succeed_job_service(db_session, job)
    assert done.status == JobStatus.SUCCEEDED.value
    assert done.progress_percent == 100
    assert done.finished_at is not None


@pytest.mark.asyncio
async def test_fail_from_running(db_session):
    user_id, space_id = await _seed_space_and_user(db_session)
    created = await create_job_service(db_session, space_id, user_id, {}, {})
    job = await db_session.get(Job, created.id)
    await start_job_service(db_session, job)
    await db_session.refresh(job)
    await update_job_progress_service(db_session, job, progress_percent=5, message="start")
    failed = await fail_job_service(db_session, job, error_code="RUNNER_ERROR", error_message="boom")
    assert failed.status == JobStatus.FAILED.value
    assert failed.error_code == "RUNNER_ERROR"


@pytest.mark.parametrize(
    "current,target",
    [
        (JobStatus.SUCCEEDED, JobStatus.RUNNING),
        (JobStatus.CANCELLED, JobStatus.QUEUED),
        (JobStatus.QUEUED, JobStatus.RUNNING),
        (JobStatus.RUNNING, JobStatus.QUEUED),
    ],
)
def test_illegal_transitions_raise(current, target):
    with pytest.raises(JobTransitionError):
        ensure_transition(current.value, target)


@pytest.mark.asyncio
async def test_list_jobs_by_status_ordered(db_session):
    user_id, space_id = await _seed_space_and_user(db_session)
    await create_job_service(db_session, space_id, user_id, {"n": "1"}, {})
    await create_job_service(db_session, space_id, user_id, {"n": "2"}, {})
    queued = await list_jobs_by_status_service(db_session, JobStatus.QUEUED)
    assert len(queued) == 2
    assert queued[0].created_at <= queued[1].created_at


@pytest.mark.asyncio
async def test_submit_and_list_jobs_api(client, db_session):
    user_id, space_id = await _seed_space_and_user(db_session)
    form_response = await client.post(
        f"/spaces/{space_id}/jobs",
        data={"prompt": "hello"},
    )
    assert form_response.status_code == 201
    body = form_response.json()
    assert body["status"] == "QUEUED"
    assert body["queue_position"] == 1

    listed = await client.get("/jobs", params={"status": "QUEUED"})
    assert listed.status_code == 200
    assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_recalculate_queue_positions(db_session):
    user_id, space_id = await _seed_space_and_user(db_session)
    j1 = await create_job_service(db_session, space_id, user_id, {}, {})
    j2 = await create_job_service(db_session, space_id, user_id, {}, {})
    j3 = await create_job_service(db_session, space_id, user_id, {}, {})
    job1 = await db_session.get(Job, j1.id)
    await cancel_job_service(db_session, job1)
    await recalculate_queue_positions(db_session)
    result = await db_session.execute(select(Job).where(Job.status == JobStatus.QUEUED.value).order_by(Job.queue_position))
    remaining = list(result.scalars().all())
    assert [j.queue_position for j in remaining] == [1, 2]
    assert {j.id for j in remaining} == {j2.id, j3.id}
