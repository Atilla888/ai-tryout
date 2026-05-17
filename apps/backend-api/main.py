from fastapi import FastAPI
from routers.spaces import router as spaces_router

app = FastAPI(title="AI Spaces API")

app.include_router(spaces_router)

@app.get("/health")
def health():
    return {"status": "ok"}
