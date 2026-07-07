"""HTTP endpoints for the current user's profile and job history."""

from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.db.session import get_db
from app.schemas.jobs import JobRead
from app.schemas.users import UserRead
from app.services.jobs import delete_job_from_history_service, list_jobs_by_user_service
from app.services.serializers import job_to_read

router = APIRouter(prefix="/me", tags=["me"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=UserRead, status_code=status.HTTP_200_OK)
async def get_current_user_profile(user: CurrentUser):
    """Returns the authenticated user's own profile."""
    return user


@router.get("/history", response_model=list[JobRead], status_code=status.HTTP_200_OK)
async def get_job_history(db: db_dependency, user: CurrentUser):
    """Returns the current user's job history."""
    jobs = await list_jobs_by_user_service(db=db, user_id=user.id)
    return [job_to_read(job) for job in jobs]


@router.delete("/history/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job_from_history(job_id: uuid.UUID, db: db_dependency, user: CurrentUser):
    """Removes one of the current user's jobs from their history."""
    await delete_job_from_history_service(db=db, public_id=job_id, user_id=user.id)
