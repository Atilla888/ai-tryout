"""
tests/integration/conftest.py

Integration-test fixtures — mirrors tests/conftest.py exactly but lives in
the integration sub-package so pytest picks it up for this folder only.

All fixtures here re-use the same patterns as the root conftest.py:
  - SQLite in-memory via aiosqlite (no external Postgres needed locally)
  - ASGI transport so no real network socket is required
  - X-Service-Token header pre-set for internal endpoints
"""

import os

# Must be set before any app import
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ALEMBIC_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("INTERNAL_SERVICE_TOKEN", "test-internal-token")
os.environ.setdefault("ARTIFACT_STORAGE_ROOT", "storage")

import uuid
import uuid6
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, insert
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db import Base, get_db
from app.main import app
from app.models import Job, Space, User

TEST_SERVICE_TOKEN = "test-internal-token"


# ---------------------------------------------------------------------------
# Patch JSONB → JSON for SQLite compatibility
# ---------------------------------------------------------------------------
def _prepare_sqlite_schema() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()


# ---------------------------------------------------------------------------
# Patch settings (storage path, token) for every test
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    storage = tmp_path / "artifacts"
    storage.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "artifact_storage_root", str(storage))
    monkeypatch.setattr(settings, "internal_service_token", TEST_SERVICE_TOKEN)


# ---------------------------------------------------------------------------
# Fresh in-memory DB per test
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def engine():
    _prepare_sqlite_schema()
    test_engine = create_async_engine(settings.database_url, echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# HTTPX async client with DB override and service token
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Service-Token": TEST_SERVICE_TOKEN},
    ) as http_client:
        yield http_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed fixture: inserts a User + Space + queued Job, returns their IDs
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def seed_space_and_user(db_session):
    """Inserts a User and a published Space. Returns (user_id, space_id)."""
    user_id = uuid6.uuid7()
    space_id = uuid6.uuid7()
    unique = uuid6.uuid7().hex

    await db_session.execute(
        insert(User).values(
            id=user_id,
            subject_id=f"test-subject-{unique}",
            idp="test",
            email=f"test-{unique}@example.com",
            display_name="Test User",
            role="user",
        )
    )
    await db_session.execute(
        insert(Space).values(
            id=space_id,
            slug=f"test-space-{unique}",
            name="Test Space",
            description="Test description",
            task_type="object-detection",
            input_types=[],
            output_types=[],
            container_image="example/yolo:latest",
            ui_config={},
            runner_config={},
            visibility="PUBLIC",
            status="PUBLISHED",
            owner_id=user_id,
        )
    )
    await db_session.commit()
    return user_id, space_id


@pytest_asyncio.fixture
async def queued_job(db_session, seed_space_and_user):
    """Inserts a Job with status QUEUED. Returns job_id."""
    user_id, space_id = seed_space_and_user
    job_id = uuid6.uuid7()

    await db_session.execute(
        insert(Job).values(
            id=job_id,
            space_id=space_id,
            user_id=user_id,
            status="QUEUED",
            input_payload={},
        )
    )
    await db_session.commit()
    return job_id
