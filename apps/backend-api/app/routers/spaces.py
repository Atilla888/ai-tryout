"""Public spaces endpoints — GET /spaces, GET /spaces/{space_id}."""

import uuid

from fastapi import APIRouter, HTTPException

from app.dependencies import DbSession
from app.schemas import SpaceDetail, SpaceListItem

router = APIRouter(prefix="/spaces", tags=["spaces"])


@router.get("", response_model=list[SpaceListItem])
async def list_spaces(db: DbSession) -> list[SpaceListItem]:
    """Return all published spaces (landing-page card grid)."""
    # TODO(S1-05): query db for published spaces
    return []


@router.get("/{space_id}", response_model=SpaceDetail)
async def get_space(space_id: uuid.UUID, db: DbSession) -> SpaceDetail:
    """Return full detail for a single published space."""
    # TODO(S1-05): query db by id, raise 404 if not found or not published
    raise HTTPException(status_code=404, detail="Space not found")
