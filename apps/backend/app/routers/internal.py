from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.service_token import verify_internal_service_token
from app.db.session import get_db
from app.schemas.artifacts import ArtifactRead
from app.schemas.internal import InternalArtifactRead, InternalJobRead, JobFailUpdate, JobProgressUpdate
from app.schemas.jobs import JobStatus
from app.services.job_transitions import JobTransitionError
from app.services.jobs import (
    create_output_artifact_service,
    fail_job_service,
    get_job_by_id_service,
    list_jobs_by_status_service,
    start_job_service,
    succeed_job_service,
    update_job_progress_service,
)

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    dependencies=[Depends(verify_internal_service_token)],
)

db_dependency = Annotated[AsyncSession, Depends(get_db)]


def _job_or_404(job):
    """Small helper so every internal route does not repeat the same 404 check."""
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get("/jobs", response_model=list[InternalJobRead])
async def list_internal_jobs(
    db: db_dependency,
    status_filter: JobStatus = Query(..., alias="status"),
):
    """What the orchestrator polls — internal integer ids, not public UUIDs."""
    return await list_jobs_by_status_service(db, status_filter)


@router.get("/jobs/{job_id}", response_model=InternalJobRead)
async def get_internal_job(db: db_dependency, job_id: int):
    job = _job_or_404(await get_job_by_id_service(db=db, job_id=job_id))
    return job


@router.patch("/jobs/{job_id}/start", response_model=InternalJobRead)
async def patch_job_start(db: db_dependency, job_id: int):
    job = _job_or_404(await get_job_by_id_service(db=db, job_id=job_id))
    try:
        return await start_job_service(db, job)
    except JobTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/jobs/{job_id}/progress", response_model=InternalJobRead)
async def patch_job_progress(db: db_dependency, job_id: int, body: JobProgressUpdate):
    job = _job_or_404(await get_job_by_id_service(db=db, job_id=job_id))
    try:
        return await update_job_progress_service(
            db,
            job,
            progress_percent=body.progress_percent,
            message=body.message,
        )
    except JobTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/jobs/{job_id}/succeed", response_model=InternalJobRead)
async def patch_job_succeed(db: db_dependency, job_id: int):
    job = _job_or_404(await get_job_by_id_service(db=db, job_id=job_id))
    try:
        return await succeed_job_service(db, job)
    except JobTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/jobs/{job_id}/fail", response_model=InternalJobRead)
async def patch_job_fail(db: db_dependency, job_id: int, body: JobFailUpdate):
    job = _job_or_404(await get_job_by_id_service(db=db, job_id=job_id))
    try:
        return await fail_job_service(
            db,
            job,
            error_code=body.error_code,
            error_message=body.error_message,
        )
    except JobTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/jobs/{job_id}/artifacts",
    response_model=InternalArtifactRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_job_artifact(
    db: db_dependency,
    job_id: int,
    artifact_type: str = Form(...),
    preview_supported: bool = Form(False),
    file: UploadFile = File(...),
):
    job = _job_or_404(await get_job_by_id_service(db=db, job_id=job_id))
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is required")
    return await create_output_artifact_service(
        db,
        job,
        file=file,
        artifact_type=artifact_type,
        preview_supported=preview_supported,
    )
