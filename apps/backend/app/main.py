from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from app.db import get_db
from app.routers import admin, artifacts, creator, internal, jobs, me, spaces
from app.schemas.common import HealthResponse

db_dependency = Annotated[AsyncSession, Depends(get_db)]

app = FastAPI(title="AI Spaces API")
app.include_router(spaces.router)
app.include_router(jobs.router)
app.include_router(artifacts.router)
app.include_router(me.router)
app.include_router(admin.router)
app.include_router(creator.router)
app.include_router(internal.router)

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")

@app.get("/health-db")
async def health_db(db: db_dependency):
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "active"}
