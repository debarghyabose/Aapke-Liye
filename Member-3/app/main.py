"""Member 3 service: verification + offline sync. Run: uvicorn app.main:app --reload"""
from fastapi import FastAPI

from app.sync import router as sync_router

app = FastAPI(title="Aapke Liye: Verification + Offline Sync", version="0.1.0")
app.include_router(sync_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
