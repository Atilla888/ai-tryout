from sqlalchemy import delete as sql_delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.schemas.spaces import SpaceCreate, SpaceUpdate
from app.db.models import Artifact, Job, Space
from uuid import UUID

# A space only shows up in the public catalog when it is both published and public.
PUBLISHED_STATUS = "PUBLISHED"
PUBLIC_VISIBILITY = "PUBLIC"


async def create_space_service(db: AsyncSession, data: SpaceCreate, owner_id: int):
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
    # Load the owner so serializers can expose the creator's public id / number.
    await db.refresh(space, attribute_names=["owner"])

    return space


async def list_spaces_service(db: AsyncSession):
    """Every space, no filtering. For admin/internal use only."""
    result = await db.execute(select(Space).options(selectinload(Space.owner)))
    return list(result.scalars().all())


async def list_public_spaces_service(db: AsyncSession):
    """The public catalog: only published spaces with public visibility.

    Draft/disabled or private spaces never leak into the anonymous Space Hub
    (US-01, spec 3.4). Creators and admins see broader results through their own
    scoped endpoints (`/creator/spaces`, `/admin/spaces`).
    """
    result = await db.execute(
        select(Space)
        .options(selectinload(Space.owner))
        .where(
            Space.status == PUBLISHED_STATUS,
            Space.visibility == PUBLIC_VISIBILITY,
        )
    )
    return list(result.scalars().all())


async def get_space_by_public_id_service(db: AsyncSession, public_id: UUID):
    result = await db.execute(
        select(Space).options(selectinload(Space.owner)).where(Space.public_id == public_id)
    )
    return result.scalar_one_or_none()


async def list_spaces_by_owner_service(db: AsyncSession, owner_id: int) -> list[Space]:
    result = await db.execute(
        select(Space).options(selectinload(Space.owner)).where(Space.owner_id == owner_id)
    )
    return list(result.scalars().all())


async def update_space_service(db: AsyncSession, space: Space, data: SpaceUpdate) -> Space:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(space, field, value)
    await db.commit()
    await db.refresh(space)
    # Reload the owner (it may have changed on an admin reassignment) so the
    # serialized response carries the creator's public id / number.
    await db.refresh(space, attribute_names=["owner"])
    return space


async def delete_space_service(db: AsyncSession, space: Space) -> None:
    """Remove a space and everything tied to it. FKs are not ON DELETE CASCADE so we do it by hand."""
    await db.execute(
        sql_delete(Artifact).where(
            Artifact.job_id.in_(select(Job.id).where(Job.space_id == space.id))
        )
    )
    await db.execute(sql_delete(Job).where(Job.space_id == space.id))
    await db.delete(space)
    await db.commit()
