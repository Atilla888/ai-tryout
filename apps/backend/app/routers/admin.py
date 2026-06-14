from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps.auth import require_role
from app.models import User
from app.schemas.spaces import AdminSpaceUpdate, SpaceDetail
from app.schemas.users import UserRead
from app.services.spaces import (
    delete_space_service,
    get_space_by_id_service,
    list_spaces_service,
    update_space_service,
)
from app.services.users import list_users_service

router = APIRouter(prefix="/admin", tags=["admin"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_role("admin"))]


@router.get("/spaces", response_model=list[SpaceDetail])
async def admin_list_spaces(db: db_dependency, _: AdminUser):
    """Return all spaces regardless of status or visibility."""
    return await list_spaces_service(db)


@router.patch("/spaces/{space_id}", response_model=SpaceDetail)
async def admin_update_space(space_id: UUID, body: AdminSpaceUpdate, db: db_dependency, _: AdminUser):
    """Edit space metadata, status, or reassign ownership."""
    space = await get_space_by_id_service(db=db, space_id=space_id)
    if space is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")
    return await update_space_service(db=db, space=space, data=body)


@router.delete("/spaces/{space_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_space(space_id: UUID, db: db_dependency, _: AdminUser):
    """Permanently remove a space and cascade-delete its jobs and artifacts."""
    space = await get_space_by_id_service(db=db, space_id=space_id)
    if space is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")
    await delete_space_service(db=db, space=space)


@router.get("/users", response_model=list[UserRead])
async def admin_list_users(db: db_dependency, _: AdminUser):
    """Return all registered users."""
    return await list_users_service(db)
