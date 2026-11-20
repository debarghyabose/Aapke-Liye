"""Member 3 service: verification + offline sync.

Run on port 8002 (the port Member 2's backend expects in MEMBER3_VERIFY_URL):
    uvicorn app.main:app --port 8002 --reload
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config, sync
from app.dashboard import router as dashboard_router
from app.store import get_store
from app.sync import router as sync_router
from app.verify import router as verify_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Restore photo fingerprints so duplicates are still caught after a restart.
    sync.dup_index.load(get_store().hashes())
    if not config.DASHBOARD_API_KEY:
        logging.getLogger("uvicorn.error").warning(
            "DASHBOARD_API_KEY is not set: /dashboard shows victim locations to anyone. "
            "Set it before sharing this server.")
    yield


app = FastAPI(title="Aapke Liye: Verification + Offline Sync", version="0.3.0", lifespan=lifespan)
# Lets Member 5's dashboard page read /dashboard from the browser. GET only:
# browsers still can't read /verify replies from other sites.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.DASHBOARD_CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["X-Dashboard-Key"],
)
app.include_router(verify_router)
app.include_router(dashboard_router)
app.include_router(sync_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
