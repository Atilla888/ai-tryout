import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
import uuid

from main import app

FAKE_SPACE_ID = uuid.uuid4()

FAKE_SPACE = MagicMock()
FAKE_SPACE.id = FAKE_SPACE_ID
FAKE_SPACE.name = "Object Detection"
FAKE_SPACE.slug = "object-detection"
FAKE_SPACE.description = "Test space"
FAKE_SPACE.task_type = "object-detection"
FAKE_SPACE.input_types = ["image"]
FAKE_SPACE.output_types = ["image"]
FAKE_SPACE.container_image = "localhost/yolo:latest"
FAKE_SPACE.resource_requirements = {"cpu": "1"}
FAKE_SPACE.ui_config = {}
FAKE_SPACE.runner_config = {}
FAKE_SPACE.visibility = "public"
FAKE_SPACE.status = "active"
from datetime import datetime, timezone
FAKE_SPACE.created_at = datetime.now(timezone.utc)
FAKE_SPACE.updated_at = datetime.now(timezone.utc)


@pytest.fixture
def mock_db():
    db = AsyncMock()
    result = MagicMock()
    return db, result


@pytest.mark.asyncio
async def test_list_spaces():
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [FAKE_SPACE]

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    from db import get_db
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/spaces")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["slug"] == "object-detection"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_space_by_id():
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = FAKE_SPACE

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    from db import get_db
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/spaces/{FAKE_SPACE_ID}")

    assert response.status_code == 200
    assert response.json()["name"] == "Object Detection"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_space_404():
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    async def override_get_db():
        yield mock_session

    from db import get_db
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/spaces/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["detail"] == "Space not found"

    app.dependency_overrides.clear()
