"""Member 3 service: verification + offline sync.

Run on port 8002 (the port Member 2's backend expects in MEMBER3_VERIFY_URL):
    uvicorn app.main:app --port 8002 --reload
"""
from fastapi import FastAPI

from app.sync import router as sync_router
from app.verify import router as verify_router

app = FastAPI(title="Aapke Liye: Verification + Offline Sync", version="0.2.0")
app.include_router(verify_router)
app.include_router(sync_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
