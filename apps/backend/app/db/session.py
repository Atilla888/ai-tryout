from collections.abc import AsyncGenerator
from app.core.config import settings
from app.db.base import Base
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

__all__ = ["Base", "async_engine", "AsyncSessionLocal", "get_db"]

async_engine = create_async_engine(settings.database_url, pool_pre_ping=True, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """One DB session per request; rolls back on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise