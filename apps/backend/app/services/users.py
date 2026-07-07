from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def list_users_service(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


async def get_user_by_public_id_service(db: AsyncSession, public_id: UUID) -> User | None:
    """Look up a user by their public UUID. Used to resolve owner reassignments."""
    result = await db.execute(select(User).where(User.public_id == public_id))
    return result.scalar_one_or_none()


async def get_user_by_subject_service(
    db: AsyncSession,
    *,
    subject_id: str,
    idp: str,
) -> User | None:
    """Look up someone by their IdP subject. None if they never signed in before."""
    result = await db.execute(
        select(User).where(
            User.subject_id == subject_id,
            User.idp == idp,
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_user_service(
    db: AsyncSession,
    *,
    subject_id: str,
    email: str,
    display_name: str | None,
    role: str,
    idp: str = "keycloak",
) -> User:
    """First login creates the row; later logins just return the existing user."""

    user = await get_user_by_subject_service(
        db,
        subject_id=subject_id,
        idp=idp,
    )

    if user is not None:
        return user

    user = User(
        subject_id=subject_id,
        idp=idp,
        email=email,
        display_name=display_name,
        role=role,
    )

    db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        # Another request may have created the same user at the same time.
        await db.rollback()

        existing = await get_user_by_subject_service(
            db,
            subject_id=subject_id,
            idp=idp,
        )

        if existing is None:
            raise

        return existing

    await db.refresh(user)
    return user
