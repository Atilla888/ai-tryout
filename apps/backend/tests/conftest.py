"""Shared fixtures for backend integration tests."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ALEMBIC_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("INTERNAL_SERVICE_TOKEN", "test-internal-token")
os.environ.setdefault("ARTIFACT_STORAGE_ROOT", "storage")

import sqlite3
import uuid

# uuid.uuid7 only exists in Python 3.14+. The tests use it for primary keys;
# fall back to the uuid6 backport (returning a plain uuid.UUID) so the suite
# also runs on Python 3.13.
if not hasattr(uuid, "uuid7"):
    import uuid6

    def _uuid7() -> uuid.UUID:
        return uuid.UUID(int=uuid6.uuid7().int)

    uuid.uuid7 = _uuid7

# Fixtures assign uuid7 values to integer primary keys; SQLite's driver rejects
# raw UUID objects, so store them as text. Same spirit as the JSONB->JSON
# compatibility shim in _prepare_sqlite_schema below.
sqlite3.register_adapter(uuid.UUID, str)

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, insert
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.db.models import Job, Space, User


def _prepare_sqlite_schema() -> None:
    """Replaces JSONB column types with JSON so SQLite can handle them in tests."""
    if not settings.database_url.startswith("sqlite"):
        return
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()

TEST_SERVICE_TOKEN = "test-internal-token"


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    """Redirects artifact storage to a temp directory and sets a known service token."""
    storage = tmp_path / "artifacts"
    storage.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "artifact_storage_root", str(storage))
    monkeypatch.setattr(settings, "internal_service_token", TEST_SERVICE_TOKEN)


@pytest_asyncio.fixture
async def engine():
    """Creates a fresh in-memory SQLite engine with the full schema, then drops it after each test."""
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
    """Provides a session scoped to a single test; rolled back automatically on teardown."""
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """HTTPX async client wired to the test DB via dependency override; pre-sets the service token header."""
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


@pytest_asyncio.fixture
async def seed_job(db_session):
    """Inserts a User, Space, and a RUNNING Job. Returns the Job ORM object.

    Integer primary keys autoincrement and ``public_id`` is generated, so tests
    can use ``job.id`` for internal endpoints and ``job.public_id`` for the
    public API.
    """
    unique = uuid.uuid4().hex

    user = User(
        subject_id=f"test-subject-{unique}",
        idp="test",
        email=f"test-{unique}@example.com",
        display_name="Test User",
        role="user",
    )
    db_session.add(user)
    await db_session.flush()

    space = Space(
        slug=f"test-space-{unique}",
        name="Test Space",
        description="Test description",
        task_type="text-to-image",
        input_types=[],
        output_types=[],
        container_image="example/image:latest",
        ui_config={},
        runner_config={},
        visibility="PUBLIC",
        status="PUBLISHED",
        owner_id=user.id,
    )
    db_session.add(space)
    await db_session.flush()

    job = Job(
        space_id=space.id,
        user_id=user.id,
        status="RUNNING",
        input_payload={},
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.commit()
    return job
