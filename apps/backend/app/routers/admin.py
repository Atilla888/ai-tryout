from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.spaces import SpaceDetail, SpaceUpdate
from app.schemas.users import UserRead

router = APIRouter(prefix="/admin", tags=["admin"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.get("/spaces", response_model=list[SpaceDetail])
async def admin_list_spaces(db: db_dependency):
    """Return all spaces regardless of status or visibility."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin space listing not implemented yet",
    )


@router.patch("/spaces/{space_id}", response_model=SpaceDetail)
async def admin_update_space(space_id: UUID, body: SpaceUpdate, db: db_dependency):
    """Edit space metadata, status, or reassign ownership."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin space update not implemented yet",
    )


@router.delete("/spaces/{space_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_space(space_id: UUID, db: db_dependency):
    """Permanently remove a space and cascade-delete its jobs."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin space deletion not implemented yet",
    )


@router.get("/users", response_model=list[UserRead])
async def admin_list_users(db: db_dependency):
    """Return all registered users."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Admin user listing not implemented yet",
    )
