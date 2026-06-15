from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid


from app.db.session import get_db
from app.deps.auth import CurrentUser
from app.schemas.jobs import JobRead
from app.schemas.users import UserRead
from app.services.jobs import list_jobs_by_user_service, delete_job_from_history_service

router = APIRouter(prefix="/me", tags=["me"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=UserRead, status_code=status.HTTP_200_OK)
async def get_current_user_profile(user: CurrentUser):
    """Return the authenticated user profile."""
    return user


@router.get("/history", response_model=list[JobRead], status_code=status.HTTP_200_OK)
async def get_job_history(db: db_dependency, user: CurrentUser):
    """Return the authenticated user's past jobs."""
    jobs = await list_jobs_by_user_service(db=db, user_id=user.id)
    return [
        JobRead(
            **{c: getattr(job, c) for c in JobRead.model_fields if hasattr(job, c)},
            space_name=job.space.name if job.space else None,
        )
        for job in jobs
    ]

@router.delete("/history/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job_from_history(job_id: uuid.UUID, db: db_dependency, user: CurrentUser):
    """Delete a job from the user's history. Returns 403 if not the owner."""
    await delete_job_from_history_service(db=db, job_id=job_id, user_id=user.id)