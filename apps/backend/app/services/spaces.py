# DB + business logic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.spaces import SpaceCreate
from app.models import Space
from uuid import UUID

async def create_space_service(db: AsyncSession, data: SpaceCreate, owner_id: UUID):
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
    result = await db.execute(select(Space))
    return list(result.scalars().all())

async def get_space_by_id_service(db: AsyncSession, space_id: UUID):
    result = await db.execute(select(Space).where(Space.id == space_id))
    return result.scalar_one_or_none()