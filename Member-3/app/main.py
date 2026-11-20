"""Member 3 service: verification + offline sync.

Run on port 8002 (the port Member 2's backend expects in MEMBER3_VERIFY_URL):
    uvicorn app.main:app --port 8002 --reload
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config, ivr, mesh, sync, whatsapp
from app.dashboard import router as dashboard_router
from app.geodata import get_geo
from app.store import get_store
from app.sync import router as sync_router
from app.verify import router as verify_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Restore photo fingerprints so duplicates are still caught after a restart.
    sync.dup_index.load(get_store().hashes())
    # Load satellite flood maps and building maps once (logs what was found).
    geo = get_geo()
    log = logging.getLogger("uvicorn.error")
    log.info("Flood maps: %s | building maps: %s",
             [n for n, _ in geo.floods.coverage] or "none", [n for n, _ in geo.buildings.coverage] or "none")
    if not config.DASHBOARD_API_KEY:
        logging.getLogger("uvicorn.error").warning(
            "DASHBOARD_API_KEY is not set: /dashboard shows victim locations to anyone. "
            "Set it before sharing this server.")
    poller = None
    if whatsapp.enabled():
        log.info("WhatsApp bot on: webhook %s/whatsapp/webhook, claims go to %s",
                 config.PUBLIC_BASE_URL or "(set PUBLIC_BASE_URL)", config.MEMBER2_API_URL)
        if config.WHATSAPP_STATUS_POLL_SECONDS > 0:
            poller = asyncio.create_task(whatsapp.status_loop())
    if not mesh.enabled():
        log.info("Mesh is off: run scripts/make_mesh_keys.py to turn it on")
    if ivr.enabled():
        log.info("IVR line on: set your Twilio number's \"A call comes in\" to %s/ivr/voice",
                 config.PUBLIC_BASE_URL or "(set PUBLIC_BASE_URL)")
    yield
    if poller:
        poller.cancel()


app = FastAPI(title="Aapke Liye: Verification + Offline Sync", version="0.3.0", lifespan=lifespan)
# Lets Member 5's dashboard page read /dashboard from the browser. GET only:
# browsers still can't read /verify replies from other sites.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.DASHBOARD_CORS_ORIGINS,
    # POST is for /mesh/envelopes from Member 4's app (a carried claim). Other POSTs need no CORS.
    allow_methods=["GET", "POST"],
    allow_headers=["X-Dashboard-Key", "Content-Type"],
)
app.include_router(verify_router)
app.include_router(dashboard_router)
app.include_router(sync_router)
app.include_router(whatsapp.router)
app.include_router(ivr.router)
app.include_router(mesh.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
