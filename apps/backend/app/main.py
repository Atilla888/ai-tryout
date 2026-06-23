"""FastAPI application entry point. Registers all routers and starts the background
cleanup task that expires old jobs and removes their artifact files every hour."""
from contextlib import asynccontextmanager

import asyncio
import logging
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.db.session import get_db, AsyncSessionLocal
from app.routers import admin, artifacts, creator, internal, jobs, me, spaces
from app.schemas.common import HealthResponse
from app.services.maintenance import cleanup_expired_jobs_and_artifacts

logger = logging.getLogger(__name__)

db_dependency = Annotated[AsyncSession, Depends(get_db)]

OPENAPI_TAGS = [
    {"name": "health", "description": "Liveness and database connectivity check"},
    {"name": "spaces", "description": "Browse and configure AI spaces"},
    {"name": "jobs", "description": "Submit jobs, poll status, cancel, list artifacts"},
    {"name": "artifacts", "description": "Preview and download job output files"},
    {"name": "internal", "description": "Runner/orchestrator callbacks (requires service token)"},
    {"name": "me", "description": "Current user profile and job history"},
    {"name": "admin", "description": "Administration"},
    {"name": "creator", "description": "Space creator and manager"},
]

CLEANUP_INTERVAL_SECONDS = 3600  # 1 hour


async def run_cleanup_once() -> None:
    """Mark expired jobs EXPIRED and delete their artifact files from disk (D3)."""
    async with AsyncSessionLocal() as db:
        result = await cleanup_expired_jobs_and_artifacts(db)
    logger.info(
        "[cleanup] expired %d job(s), removed %d artifact file(s)",
        result.jobs_expired,
        result.artifacts_removed,
    )


async def _cleanup_loop() -> None:
    """Background loop: runs the expiration cleanup every hour."""
    while True:
        try:
            await run_cleanup_once()
        except Exception:
            logger.exception("[cleanup] Error during cleanup")
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown. Starts the background cleanup loop
    on startup and cancels it cleanly when the server shuts down."""
    logging.basicConfig(level=logging.INFO)
    cleanup_task = asyncio.create_task(_cleanup_loop())

    api_routes = [r for r in app.routes if getattr(r, "methods", None)]
    logger.info("[startup] Registered %d API routes", len(api_routes))
    for route in sorted(api_routes, key=lambda r: r.path):
        methods = ",".join(sorted(route.methods - {"HEAD", "OPTIONS"}))
        logger.info("  %-7s %s", methods, route.path)
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
