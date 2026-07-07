"""HTTP endpoints for admin management of spaces and users."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.auth import require_role
from app.db.models import User
from app.schemas.spaces import AdminSpaceUpdate, SpaceDetail, SpaceUpdate
from app.schemas.users import UserRead
from app.services.spaces import (
    delete_space_service,
    get_space_by_public_id_service,
    list_spaces_service,
    update_space_service,
)
from app.services.users import get_user_by_public_id_service, list_users_service

router = APIRouter(prefix="/admin", tags=["admin"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_role("admin"))]


@router.get("/spaces", response_model=list[SpaceDetail])
async def admin_list_spaces(db: db_dependency, _: AdminUser):
    """Every space, no filtering. For admin/internal use only."""
    return await list_spaces_service(db)


@router.patch("/spaces/{space_id}", response_model=SpaceDetail)
async def admin_update_space(space_id: UUID, body: AdminSpaceUpdate, db: db_dependency, _: AdminUser):
    """Updates any space's fields regardless of ownership; admin only."""
    space = await get_space_by_public_id_service(db=db, public_id=space_id)
    if space is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")

    # Reassign ownership by the target user's public UUID → internal row id.
    if body.owner_id is not None:
        new_owner = await get_user_by_public_id_service(db=db, public_id=body.owner_id)
        if new_owner is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner not found")
        space.owner_id = new_owner.id

    # Apply the remaining fields (owner_id is handled above, not a plain column set).
    other_fields = SpaceUpdate(**body.model_dump(exclude_unset=True, exclude={"owner_id"}))
    return await update_space_service(db=db, space=space, data=other_fields)


@router.delete("/spaces/{space_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_space(space_id: UUID, db: db_dependency, _: AdminUser):
    """Hard delete — jobs and artifacts go too."""
    space = await get_space_by_public_id_service(db=db, public_id=space_id)
    if space is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")
    await delete_space_service(db=db, space=space)


@router.get("/users", response_model=list[UserRead])
async def admin_list_users(db: db_dependency, _: AdminUser):
    """Every registered user; admin only."""
    return await list_users_service(db)
