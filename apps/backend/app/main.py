from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from app.db import get_db
from app.routers import spaces, jobs, internal

db_dependency = Annotated[AsyncSession, Depends(get_db)]

app = FastAPI(title="AI Spaces API")
app.include_router(spaces.router)
app.include_router(jobs.router)
app.include_router(internal.router)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/health-db")
async def health_db(db: db_dependency):
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "active"}
