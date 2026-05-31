from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from app.db import get_db
from app.deps.auth import CurrentUser
from app.models import User
from app.schemas.artifacts import ArtifactRead
from app.schemas.jobs import JobRead, JobStatus, JobSubmitResponse, TERMINAL_JOB_STATUSES
from app.services.artifacts import list_artifacts_by_job_service
from app.services.jobs import (
    cancel_job_service,
    create_job_service,
    get_job_by_id_service,
    list_jobs_by_status_service,
)
from app.services.job_transitions import JobTransitionError
from app.services.spaces import get_space_by_id_service

router = APIRouter(tags=["jobs"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]


def _ensure_owner_or_admin(job, user: User) -> None:
    if job.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your job")


@router.post("/spaces/{space_id}/jobs", response_model=JobSubmitResponse, status_code=status.HTTP_201_CREATED)
async def create_job(request: Request, db: db_dependency, space_id: UUID, user: CurrentUser):
    form = await request.form()
    if not form:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job input is required")

    space = await get_space_by_id_service(db=db, space_id=space_id)
    if space is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")

    input_payload: dict[str, str] = {}
    files: dict[str, UploadFile] = {}

    for key, value in form.items():
        if isinstance(value, UploadFile):
            if value.filename:
                files[key] = value
        else:
            input_payload[key] = str(value)

    if not input_payload and not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job input is required")

    return await create_job_service(
        db=db,
        space_id=space_id,
        user_id=user.id,
        input_payload=input_payload,
        files=files,
    )


@router.get("/jobs", response_model=list[JobRead])
async def list_jobs(db: db_dependency, status_filter: JobStatus = Query(..., alias="status")):
    return await list_jobs_by_status_service(db, status_filter)


@router.get("/jobs/{job_id}", response_model=JobRead, status_code=status.HTTP_200_OK)
async def get_job(db: db_dependency, job_id: UUID):
    job = await get_job_by_id_service(db=db, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/artifacts", response_model=list[ArtifactRead])
async def list_job_artifacts(db: db_dependency, job_id: UUID):
    job = await get_job_by_id_service(db=db, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return await list_artifacts_by_job_service(db, job_id)


@router.post("/jobs/{job_id}/cancel", response_model=JobRead, status_code=status.HTTP_200_OK)
async def cancel_job(db: db_dependency, job_id: UUID, user: CurrentUser):
    job = await get_job_by_id_service(db=db, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    _ensure_owner_or_admin(job, user)

    try:
        current_status = JobStatus(job.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Unknown job status {job.status}") from exc
    if current_status in TERMINAL_JOB_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Cannot cancel job with status {job.status}")

    try:
        return await cancel_job_service(db=db, job=job)
    except JobTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
