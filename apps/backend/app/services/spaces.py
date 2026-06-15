# DB + business logic
from sqlalchemy import delete as sql_delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.spaces import SpaceCreate, SpaceUpdate
from app.db.models import Artifact, Job, Space
from uuid import UUID

async def create_space_service(db: AsyncSession, data: SpaceCreate, owner_id: UUID):
    """Creates and persists a new space owned by owner_id."""
    space = Space(
        slug=data.slug,
        name=data.name,
        description=data.description,
        task_type=data.task_type,
        input_types=data.input_types,
        output_types=data.output_types,
        container_image=data.container_image,
        ui_config=data.ui_config,
        runner_config=data.runner_config,
        visibility=data.visibility,
        status=data.status,
        owner_id=owner_id,
    )

    db.add(space)
    await db.commit()
    await db.refresh(space)

    return space

async def list_spaces_service(db: AsyncSession):
    """Returns all spaces. Filtering by status/visibility is left to the caller."""
    result = await db.execute(select(Space))
    return list(result.scalars().all())

async def get_space_by_id_service(db: AsyncSession, space_id: UUID):
    """Looks up a space by its UUID. Returns None if not found."""
    result = await db.execute(select(Space).where(Space.id == space_id))
    return result.scalar_one_or_none()

async def list_spaces_by_owner_service(db: AsyncSession, owner_id: UUID) -> list[Space]:
    """Returns all spaces owned by owner_id, used to populate the creator dashboard."""
    result = await db.execute(select(Space).where(Space.owner_id == owner_id))
    return list(result.scalars().all())

async def update_space_service(db: AsyncSession, space: Space, data: SpaceUpdate) -> Space:
    """Applies a partial update to a space. Only fields explicitly set in data are written
    (exclude_unset=True) so callers can safely send partial payloads."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(space, field, value)
    await db.commit()
    await db.refresh(space)
    return space

async def delete_space_service(db: AsyncSession, space: Space) -> None:
    """Deletes a space and cascade-removes all related jobs and artifacts.
    The cascade is done manually because the DB foreign keys don't have ON DELETE CASCADE."""
    await db.execute(
        sql_delete(Artifact).where(
            Artifact.job_id.in_(select(Job.id).where(Job.space_id == space.id))
        )
    )
    await db.execute(sql_delete(Job).where(Job.space_id == space.id))
    await db.delete(space)
    await db.commit()