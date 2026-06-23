"""Minimal load test for the AI-Spaces backend (T8, optional Kür).

Fires many concurrent requests at the two cheap read endpoints — ``/health`` and
``GET /spaces`` — and reports throughput and latency percentiles. The app runs
in-process via httpx' ASGI transport against an in-memory SQLite DB, so no
separate server or database is required.

Run from apps/backend:

    python scripts/loadtest.py                 # defaults: 2000 requests, 50 concurrent
    python scripts/loadtest.py 5000 100        # total requests, concurrency

This is a smoke-level load check, not a production benchmark (no real network
hop). For a heavier test use a dedicated tool (e.g. jMeter or Locust) against a
running server.
"""

import asyncio
import os
import statistics
import sys
import time

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("INTERNAL_SERVICE_TOKEN", "load-test-token")
os.environ.setdefault("ARTIFACT_STORAGE_ROOT", "storage")

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import JSON  # noqa: E402
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.models import Space, User  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


def _swap_jsonb_for_sqlite() -> None:
    """SQLite cannot handle JSONB columns; downgrade them to JSON for the test DB."""
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()


async def _seed(session_factory) -> None:
    """Insert a handful of published, public spaces so GET /spaces has work to do."""
    async with session_factory() as session:
        owner = User(
            subject_id="load-owner",
            idp="loadtest",
            email="load-owner@example.com",
            display_name="Load Owner",
            role="space_creator",
        )
        session.add(owner)
        await session.flush()
        for i in range(5):
            session.add(
                Space(
                    slug=f"load-space-{i}",
                    name=f"Load Space {i}",
                    description="Seeded for the load test",
                    task_type="Text",
                    input_types=[],
                    output_types=[],
                    container_image="example/image:latest",
                    ui_config={"inputs": []},
                    runner_config={},
                    visibility="PUBLIC",
                    status="PUBLISHED",
                    owner_id=owner.id,
                )
            )
        await session.commit()


async def _run_endpoint(client: AsyncClient, path: str, total: int, concurrency: int) -> None:
    """Fire `total` GET requests at `path` with at most `concurrency` in flight."""
    semaphore = asyncio.Semaphore(concurrency)
    latencies: list[float] = []
    errors = 0

    async def one_request() -> None:
        nonlocal errors
        async with semaphore:
            start = time.perf_counter()
            try:
                response = await client.get(path)
                if response.status_code >= 400:
                    errors += 1
            except Exception:
                errors += 1
            latencies.append((time.perf_counter() - start) * 1000.0)

    started = time.perf_counter()
    await asyncio.gather(*(one_request() for _ in range(total)))
    elapsed = time.perf_counter() - started

    latencies.sort()

    def pct(p: float) -> float:
        if not latencies:
            return 0.0
        idx = min(len(latencies) - 1, int(p / 100 * len(latencies)))
        return latencies[idx]

    print(f"\n{path}")
    print(f"  requests        : {total} ({concurrency} concurrent)")
    print(f"  duration        : {elapsed:.2f}s")
    print(f"  throughput      : {total / elapsed:.0f} req/s")
    print(f"  errors          : {errors}")
    print(f"  latency  p50/p95/p99 : {pct(50):.1f} / {pct(95):.1f} / {pct(99):.1f} ms")
    print(f"  latency  min/mean/max: {latencies[0]:.1f} / {statistics.mean(latencies):.1f} / {latencies[-1]:.1f} ms")


async def main() -> None:
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    _swap_jsonb_for_sqlite()
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await _seed(session_factory)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://loadtest") as client:
            print(f"Load test: {total} requests, concurrency {concurrency}")
            await _run_endpoint(client, "/health", total, concurrency)
            await _run_endpoint(client, "/spaces", total, concurrency)
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
