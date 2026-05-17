"""Authenticated user profile and history endpoints — /me."""

from fastapi import APIRouter

from app.dependencies import DbSession
from app.schemas import JobRead, UserRead

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=UserRead)
async def get_current_user(db: DbSession) -> UserRead:
    """Return the profile of the currently authenticated user."""
    # TODO(Sprint 2): resolve user from JWT, return profile
    raise NotImplementedError


@router.get("/history", response_model=list[JobRead])
async def get_job_history(db: DbSession) -> list[JobRead]:
    """Return the authenticated user's past jobs."""
    # TODO(Sprint 2): filter jobs by current user, apply retention rules
    raise NotImplementedError
