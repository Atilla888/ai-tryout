import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db import get_db
from models import Space, SpaceStatus, SpaceVisibility
from schemas.space import SpaceListItem, SpaceDetail

router = APIRouter(prefix="/spaces", tags=["spaces"])


@router.get("", response_model=list[SpaceListItem])
async def list_spaces(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Space).where(
            Space.status == SpaceStatus.active,
            Space.visibility == SpaceVisibility.public,
        )
    )
    return result.scalars().all()


@router.get("/{space_id}", response_model=SpaceDetail)
async def get_space(space_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Space).where(
            Space.id == space_id,
            Space.status == SpaceStatus.active,
            Space.visibility == SpaceVisibility.public,
        )
    )
    space = result.scalar_one_or_none()
    if space is None:
        raise HTTPException(status_code=404, detail="Space not found")
    return space
