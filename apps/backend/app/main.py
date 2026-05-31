from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.db import get_db
from app.routers import admin, artifacts, creator, internal, jobs, me, spaces
from app.schemas.common import HealthResponse

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    api_routes = [r for r in app.routes if getattr(r, "methods", None)]
    print(f"[startup] Registered {len(api_routes)} API routes")
    for route in sorted(api_routes, key=lambda r: r.path):
        methods = ",".join(sorted(route.methods - {"HEAD", "OPTIONS"}))
        print(f"  {methods:7} {route.path}")
    yield


app = FastAPI(
    title="AI Spaces API",
    version="0.2.0",
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
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
    return HealthResponse(status="ok")


@app.get("/health-db", tags=["health"])
async def health_db(db: db_dependency):
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "active"}
