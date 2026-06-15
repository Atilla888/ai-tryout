"""FastAPI application entry point. Registers all routers and starts the background
cleanup task that removes expired jobs and artifacts every hour."""
from contextlib import asynccontextmanager

import asyncio
from datetime import datetime, timezone
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.db.session import get_db, AsyncSessionLocal
from app.routers import admin, artifacts, creator, internal, jobs, me, spaces
from app.schemas.common import HealthResponse
from app.db.models import Artifact, Job

db_dependency = Annotated[AsyncSession, Depends(get_db)]

OPENAPI_TAGS = [
    {"name": "health", "description": "Liveness and database connectivity check"},
    {"name": "spaces", "description": "Browse and configure AI spaces"},
    {"name": "jobs", "description": "Submit jobs, poll status, cancel, list artifacts"},
    {"name": "artifacts", "description": "Preview and download job output files"},
    {"name": "internal", "description": "Runner/orchestrator callbacks (requires service token)"},
    {"name": "me", "description": "Current user profile and job history"},
    {"name": "admin", "description": "Administration (stubs)"},
    {"name": "creator", "description": "Space creator and manager (stubs)"},
]

CLEANUP_INTERVAL_SECONDS = 3600  # 1 hour


async def cleanup_expired_artifacts() -> None:
    """Delete artifact records (and their jobs) where expires_at has passed."""
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        #delete expired artifacts first
        await db.execute(delete(Artifact).where(Artifact.expires_at < now))
        # Delete jobs with no remaining artifacts that are also expired
        await db.execute(delete(Job).where(Job.expires_at < now))
        await db.commit()
    print(f"[cleanup] Expired artifacts and jobs cleaned up at {now.isoformat()}")


async def _cleanup_loop() -> None:
    """Background loop: runs cleanup every hour."""
    while True:
        try:
            await cleanup_expired_artifacts()
        except Exception as exc:
            print(f"[cleanup] Error during cleanup: {exc}")
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown. Starts the background cleanup loop
    on startup and cancels it cleanly when the server shuts down."""
    cleanup_task = asyncio.create_task(_cleanup_loop())

    api_routes = [r for r in app.routes if getattr(r, "methods", None)]
    print(f"[startup] Registered {len(api_routes)} API routes")
    for route in sorted(api_routes, key=lambda r: r.path):
        methods = ",".join(sorted(route.methods - {"HEAD", "OPTIONS"}))
        print(f"  {methods:7} {route.path}")
    yield

    # Graceful shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="AI Spaces API",
    version="0.2.0",
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(spaces.router)
app.include_router(jobs.router)
app.include_router(artifacts.router)
app.include_router(me.router)
app.include_router(admin.router)
app.include_router(creator.router)
app.include_router(internal.router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health():
    """Simple liveness probe. Returns ok as long as the process is running."""
    return HealthResponse(status="ok")


@app.get("/health-db", tags=["health"])
async def health_db(db: db_dependency):
    """Readiness probe that also checks database connectivity by running a trivial query."""
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "active"}
