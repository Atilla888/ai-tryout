from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.service_token import verify_internal_service_token
from app.db.session import get_db
from app.schemas.artifacts import ArtifactRead
from app.schemas.internal import (
    InternalArtifactRead,
    InternalJobRead,
    JobExecutionData,
    JobFailUpdate,
    JobProgressUpdate,
    RunnerInput,
    RunnerInputArtifact,
)
from app.schemas.jobs import JobStatus
from app.services.artifacts import (
    artifact_absolute_path,
    ensure_artifact_available,
    get_artifact_by_id_service,
    list_input_artifacts_by_job_id_service,
)
from app.services.job_transitions import JobTransitionError
from app.services.jobs import (
    create_output_artifact_service,
    fail_job_service,
    finalize_cancellation_service,
    get_job_by_id_service,
    get_job_with_space_by_id_service,
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


@router.get("/jobs/{job_id}/execution-data", response_model=JobExecutionData)
async def get_job_execution_data(db: db_dependency, job_id: int):
    """What the orchestrator needs to launch the worker (spec 5.3, F2)."""
    job = _job_or_404(await get_job_with_space_by_id_service(db=db, job_id=job_id))
    return JobExecutionData(
        job_id=job.id,
        space_id=job.space_id,
        space_public_id=str(job.space.public_id),
        runner_image=job.space.container_image,
        runner_config=job.space.runner_config or {},
        input_reference=job.id,
    )


@router.get("/jobs/{job_id}/runner-input", response_model=RunnerInput)
async def get_runner_input(db: db_dependency, job_id: int):
    """The runner pulls its form payload and the list of INPUT files here (D4)."""
    job = _job_or_404(await get_job_by_id_service(db=db, job_id=job_id))
    artifacts = await list_input_artifacts_by_job_id_service(db, job.id)

    # input_payload["input_artifacts"] maps a form field name -> artifact db id (str).
    field_by_artifact_id: dict[int, str] = {}
    mapping = (job.input_payload or {}).get("input_artifacts", {})
    if isinstance(mapping, dict):
        for field_name, artifact_id in mapping.items():
            try:
                field_by_artifact_id[int(artifact_id)] = field_name
            except (TypeError, ValueError):
                continue

    input_artifacts = [
        RunnerInputArtifact(
            id=artifact.id,
            field_name=field_by_artifact_id.get(artifact.id),
            file_name=artifact.file_name,
            content_type=artifact.content_type,
            size_bytes=artifact.size_bytes,
            content_url=f"/internal/artifacts/{artifact.id}/content",
        )
        for artifact in artifacts
    ]

    return RunnerInput(
        job_id=job.id,
        space_id=job.space_id,
        input_payload=job.input_payload or {},
        input_artifacts=input_artifacts,
    )


@router.get("/artifacts/{artifact_id}/content")
async def get_internal_artifact_content(db: db_dependency, artifact_id: int) -> FileResponse:
    """Download an artifact's bytes by internal id (used for INPUT files, D4)."""
    artifact = await get_artifact_by_id_service(db, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    try:
        ensure_artifact_available(artifact)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return FileResponse(
        path=artifact_absolute_path(artifact),
        media_type=artifact.content_type,
        filename=artifact.file_name,
    )


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


@router.patch("/jobs/{job_id}/cancelled", response_model=InternalJobRead)
async def patch_job_cancelled(db: db_dependency, job_id: int):
    """Orchestrator confirms the worker is gone; finalize CANCELLING -> CANCELLED (D2)."""
    job = _job_or_404(await get_job_by_id_service(db=db, job_id=job_id))
    try:
        return await finalize_cancellation_service(db, job)
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
