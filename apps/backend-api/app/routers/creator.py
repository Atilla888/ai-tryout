"""Space creator endpoints — /creator."""

import uuid

from fastapi import APIRouter

from app.dependencies import DbSession
from app.schemas import SpaceCreate, SpaceDetail, SpaceUpdate

router = APIRouter(prefix="/creator", tags=["creator"])


@router.post("/spaces", response_model=SpaceDetail, status_code=201)
async def create_space(body: SpaceCreate, db: DbSession) -> SpaceDetail:
    """Create a new space owned by the authenticated creator."""
    # TODO(Sprint 2): enforce creator role, insert space record
    raise NotImplementedError


@router.get("/spaces", response_model=list[SpaceDetail])
async def list_my_spaces(db: DbSession) -> list[SpaceDetail]:
    """Return all spaces owned by the authenticated creator."""
    # TODO(Sprint 2): enforce creator role, filter by owner_id
    raise NotImplementedError


@router.patch("/spaces/{space_id}", response_model=SpaceDetail)
async def update_space(
    space_id: uuid.UUID, body: SpaceUpdate, db: DbSession
) -> SpaceDetail:
    """Update metadata or configuration for an owned space."""
    # TODO(Sprint 2): enforce creator role, validate ownership
    raise NotImplementedError


@router.post("/spaces/{space_id}/validate")
async def validate_space_config(space_id: uuid.UUID, db: DbSession) -> dict:
    """Validate the space configuration and runner contract before publishing."""
    # TODO(Sprint 2): enforce creator role, run schema validation
    raise NotImplementedError
