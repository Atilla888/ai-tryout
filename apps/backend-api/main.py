from fastapi import FastAPI

app = FastAPI(title="AI Spaces API")

@app.get("/health")
def health():
    return {"status": "ok"}
