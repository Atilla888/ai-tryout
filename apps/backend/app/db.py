from app.config import settings
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

engine = create_async_engine(settings.database_url, pool_pre_ping=True, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# async with means: 1) Open the session 2) when the block ends, run the cleanup (await session.close()) under the hood
# pool_pre_ping=True -> validate pooled connections. If a connection from the pool is idle, it opens a new one
# echo -> log SQL to the console or not.