from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.spaces import SpaceCreate, SpaceDetail, SpaceUpdate

router = APIRouter(prefix="/creator", tags=["creator"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.post("/spaces", response_model=SpaceDetail, status_code=status.HTTP_201_CREATED)
async def create_space(body: SpaceCreate, db: db_dependency):
    """Create a new space owned by the authenticated creator."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Creator space creation not implemented yet")


@router.get("/spaces", response_model=list[SpaceDetail])
async def list_my_spaces(db: db_dependency):
    """Return all spaces owned by the authenticated creator."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Creator space listing not implemented yet")


@router.patch("/spaces/{space_id}", response_model=SpaceDetail)
async def update_space(space_id: UUID, body: SpaceUpdate, db: db_dependency):
    """Update metadata or configuration for an owned space."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Creator space update not implemented yet")


@router.post("/spaces/{space_id}/validate")
async def validate_space_config(space_id: UUID, db: db_dependency):
    """Validate the space configuration and runner contract before publishing."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Space validation not implemented yet")
