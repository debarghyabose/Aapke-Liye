from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (registers tables)
from .config import CORS_ORIGINS, MEMBER1_AI_URL, MEMBER3_VERIFY_URL, SUPPORTED_LANGUAGES
from .db import Base, engine
from .routers import claims, status
from .services.relief import load_sdrf_rules

Base.metadata.create_all(engine)  # fine for the hackathon; use Alembic later

app = FastAPI(title="Aapke Liye — Core Backend", version="0.1.0",
              description="Member 2: claims, uploads, SDRF relief calculation and relief form PDF.")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"],
                   allow_headers=["*"])

app.include_router(claims.router)
app.include_router(status.router)


@app.get("/health", tags=["meta"])
def health():
    return {"ok": True, "languages": SUPPORTED_LANGUAGES,
            "member1_ai": MEMBER1_AI_URL or "mock", "member3_verify": MEMBER3_VERIFY_URL or "mock"}


@app.get("/rules/sdrf", tags=["meta"])
def sdrf_rules():
    return load_sdrf_rules()
