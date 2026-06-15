from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def list_users_service(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


async def get_user_by_subject_service(db: AsyncSession, subject_id: str) -> User | None:
    result = await db.execute(select(User).where(User.subject_id == subject_id))
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
    """Just-in-time provisioning: first valid token from a new `sub` creates a row."""
    user = await get_user_by_subject_service(db, subject_id)
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
        # Concurrent first-login for the same subject: fall back to the existing row.
        await db.rollback()
        existing = await get_user_by_subject_service(db, subject_id)
        if existing is None:
            raise
        return existing

    await db.refresh(user)
    return user
