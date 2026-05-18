from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.jobs import JobRead
from app.schemas.users import UserRead

router = APIRouter(prefix="/me", tags=["me"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=UserRead)
async def get_current_user(db: db_dependency):
    """Return the profile of the currently authenticated user."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Authentication not implemented yet")


@router.get("/history", response_model=list[JobRead])
async def get_job_history(db: db_dependency):
    """Return the authenticated user's past jobs."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Job history not implemented yet")
