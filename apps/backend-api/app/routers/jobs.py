"""Job lifecycle endpoints — /spaces/{space_id}/jobs and /jobs/{job_id}."""

import uuid

from fastapi import APIRouter, HTTPException

from app.dependencies import DbSession
from app.schemas import ArtifactRead, JobCreate, JobRead, JobSubmitResponse

router = APIRouter(tags=["jobs"])


@router.post("/spaces/{space_id}/jobs", response_model=JobSubmitResponse, status_code=201)
async def submit_job(space_id: uuid.UUID, body: JobCreate, db: DbSession) -> JobSubmitResponse:
    """Create a new job for the given space in QUEUED state."""
    # TODO(S1-06): validate space exists, create job record, return id + queue_position
    raise HTTPException(status_code=404, detail="Space not found")


@router.get("/jobs/{job_id}", response_model=JobRead)
async def get_job(job_id: uuid.UUID, db: DbSession) -> JobRead:
    """Return current job status and progress."""
    # TODO(S1-06): fetch job from db, raise 404 if not found
    raise HTTPException(status_code=404, detail="Job not found")


@router.post("/jobs/{job_id}/cancel", response_model=JobRead)
async def cancel_job(job_id: uuid.UUID, db: DbSession) -> JobRead:
    """Cancel a QUEUED or RUNNING job."""
    # TODO(S1-06): transition job to CANCELLED, return updated record
    raise HTTPException(status_code=404, detail="Job not found")


@router.get("/jobs/{job_id}/artifacts", response_model=list[ArtifactRead])
async def list_job_artifacts(job_id: uuid.UUID, db: DbSession) -> list[ArtifactRead]:
    """Return artifact metadata for a completed job."""
    # TODO(S1-07): fetch artifacts by job_id
    raise HTTPException(status_code=404, detail="Job not found")
