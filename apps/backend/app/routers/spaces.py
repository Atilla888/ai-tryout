from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_role
from app.db.models import User
from app.db.session import get_db
from app.schemas.spaces import SpaceCreate, SpaceRead
from app.services.spaces import create_space_service, get_space_by_public_id_service, list_public_spaces_service

router = APIRouter(prefix="/spaces", tags=["spaces"])
db_dependency = Annotated[AsyncSession, Depends(get_db)]
CreatorUser = Annotated[User, Depends(require_role("space_creator", "admin"))]


@router.post("", response_model=SpaceRead, status_code=status.HTTP_201_CREATED)
async def create_space(db: db_dependency, data: SpaceCreate, creator: CreatorUser):
    try:
        return await create_space_service(db=db, data=data, owner_id=creator.id)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Space with this slug already exists for this owner")


@router.get("", response_model=list[SpaceRead], status_code=status.HTTP_200_OK)
async def get_spaces(db: db_dependency):
    """Public Space Hub catalog — only published, public spaces (D1)."""
    return await list_public_spaces_service(db)


@router.get("/{space_id}", response_model=SpaceRead, status_code=status.HTTP_200_OK)
async def get_space_by_id(db: db_dependency, space_id: UUID):
    space = await get_space_by_public_id_service(db=db, public_id=space_id)
    if space is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space not found by this id")
    return space
