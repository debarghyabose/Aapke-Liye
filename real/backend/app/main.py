"""
Aapke Liye — Standalone Unified Backend
Connects directly to Firebase Firestore, Gemini 3.5 Flash Multilingual AI,
and Cloudinary / Local Storage on Google Cloud Project trusty-obelisk-515402-p3.
"""
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .routers import claims, mesh, meta, speech, staff, status, vault

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("aapke_liye")

app = FastAPI(
    title="Aapke Liye (आपके लिए) — Standalone Disaster Relief Infrastructure",
    description="Unified Backend & APIs powered by Firebase Firestore and Google Gemini AI.",
    version="2.0.0",
)

# Enable CORS for local dev and Cloud Run domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# On Vercel the backend is exposed at /api/*. Strip that prefix so the same routes work
# both there and at the root (Docker / Cloud Run); root_path keeps /docs pointing at /api/openapi.json.
@app.middleware("http")
async def strip_api_prefix(request: Request, call_next):
    path = request.scope["path"]
    if path == "/api" or path.startswith("/api/"):
        request.scope["path"] = path[4:] or "/"
        request.scope["root_path"] = request.scope.get("root_path", "") + "/api"
    return await call_next(request)


# Include core routers
app.include_router(claims.router)
app.include_router(vault.router)
app.include_router(status.router)
app.include_router(staff.router)
app.include_router(mesh.router)
app.include_router(speech.router)
app.include_router(meta.router)

# Mount local storage directory
config.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(config.STORAGE_DIR)), name="storage")

# Serve Frontend SPA static build if present
DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if not DIST_DIR.exists():
    # In container deployment, static files might be at /var/www/html or /app/frontend/dist
    container_dist = Path("/var/www/html")
    if container_dist.exists() and (container_dist / "index.html").exists():
        DIST_DIR = container_dist

if DIST_DIR.exists() and (DIST_DIR / "index.html").exists():
    assets_dir = DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Allow API routes to be handled by routers
        file_path = DIST_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DIST_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=config.PORT, reload=True)
