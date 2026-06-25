from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.auth import require_role
from app.db.models import User
from app.schemas.spaces import SpaceCreate, SpaceDetail, SpaceUpdate
from app.schemas.validation import ValidationResult
from app.services.spaces import (
    create_space_service,
    get_space_by_public_id_service,
    list_spaces_by_owner_service,
    update_space_service,
)
from app.services.validation import validate_space_config

router = APIRouter(prefix="/creator", tags=["creator"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]
CreatorUser = Annotated[User, Depends(require_role("space_creator", "admin"))]


@router.post("/spaces", response_model=SpaceDetail, status_code=status.HTTP_201_CREATED)
async def create_space(body: SpaceCreate, db: db_dependency, creator: CreatorUser):
    try:
        return await create_space_service(db=db, data=body, owner_id=creator.id)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Space with this slug already exists for this owner",
        )


@router.get("/spaces", response_model=list[SpaceDetail])
async def list_my_spaces(db: db_dependency, creator: CreatorUser):
    return await list_spaces_by_owner_service(db=db, owner_id=creator.id)


@router.patch("/spaces/{space_id}", response_model=SpaceDetail)
async def update_space(space_id: UUID, body: SpaceUpdate, db: db_dependency, creator: CreatorUser):
    space = await get_space_by_public_id_service(db=db, public_id=space_id)
    if space is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")
    if space.owner_id != creator.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this space")
    return await update_space_service(db=db, space=space, data=body)


@router.post("/spaces/{space_id}/validate", response_model=ValidationResult)
async def validate_space_config_route(space_id: UUID, db: db_dependency, creator: CreatorUser):
    space = await get_space_by_public_id_service(db=db, public_id=space_id)
    if space is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found")
    if space.owner_id != creator.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this space")
    return validate_space_config(space)
