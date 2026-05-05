"""Administrator-only management endpoints — /admin."""

import uuid

from fastapi import APIRouter

from app.dependencies import DbSession
from app.schemas import SpaceDetail, SpaceUpdate, UserRead

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/spaces", response_model=list[SpaceDetail])
async def admin_list_spaces(db: DbSession) -> list[SpaceDetail]:
    """Return all spaces regardless of status or visibility."""
    # TODO(Sprint 2): enforce admin role, query all spaces
    raise NotImplementedError


@router.patch("/spaces/{space_id}", response_model=SpaceDetail)
async def admin_update_space(
    space_id: uuid.UUID, body: SpaceUpdate, db: DbSession
) -> SpaceDetail:
    """Edit space metadata, status, or reassign ownership."""
    # TODO(Sprint 2): enforce admin role, apply updates
    raise NotImplementedError


@router.delete("/spaces/{space_id}", status_code=204)
async def admin_delete_space(space_id: uuid.UUID, db: DbSession) -> None:
    """Permanently remove a space and cascade-delete its jobs."""
    # TODO(Sprint 2): enforce admin role, require confirmation token
    raise NotImplementedError


@router.get("/users", response_model=list[UserRead])
async def admin_list_users(db: DbSession) -> list[UserRead]:
    """Return all registered users."""
    # TODO(Sprint 2): enforce admin role
    raise NotImplementedError
