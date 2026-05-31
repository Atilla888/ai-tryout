from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps.auth import CurrentUser
from app.schemas.jobs import JobRead
from app.schemas.users import UserRead
from app.services.jobs import list_jobs_by_user_service

router = APIRouter(prefix="/me", tags=["me"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=UserRead, status_code=status.HTTP_200_OK)
async def get_current_user_profile(user: CurrentUser):
    """Return the authenticated user profile."""
    return user


@router.get("/history", response_model=list[JobRead], status_code=status.HTTP_200_OK)
async def get_job_history(db: db_dependency, user: CurrentUser):
    """Return the authenticated user's past jobs."""
    return await list_jobs_by_user_service(db=db, user_id=user.id)
