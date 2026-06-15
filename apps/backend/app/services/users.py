from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def list_users_service(db: AsyncSession) -> list[User]:
    """Returns all registered users ordered by their registration date."""
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


async def get_user_by_subject_service(
    db: AsyncSession,
    *,
    subject_id: str,
    idp: str,
) -> User | None:
    """Looks up a user by their IdP subject_id. Returns None if they have never logged in before.
    idp is always 'keycloak' for now but kept for future multi-IdP support."""
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
    """Just-in-time provisioning: first valid token from a new subject creates a user row."""

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
