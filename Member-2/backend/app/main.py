import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from . import models  # noqa: F401  (registers tables)
from .config import SUPPORTED_LANGUAGES, settings
from .db import create_tables, engine
from .logs import request_context, setup_logging
from .routers import claims, staff, status
from .security import limiter
from .services.relief import load_sdrf_rules, rules_are_sample
from .uploads import MAX_REQUEST_BYTES

setup_logging(settings.log_level)
settings.validate()  # fail fast: refuse unsafe production settings before serving anything
load_sdrf_rules()    # fail fast: rules/sdrf_rules.json must have a valid structure


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.is_production:   # production runs `alembic upgrade head` instead
        await create_tables()
    yield
    await engine.dispose()


app = FastAPI(title="Aapke Liye — Core Backend", version="1.0.0", lifespan=lifespan,
              description="Member 2: claims, uploads, SDRF relief calculation and relief form PDF.")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    """Reject oversized uploads from Content-Length before reading the body. Also cap the
    body size at the reverse proxy (e.g. nginx client_max_body_size 16m)."""
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_REQUEST_BYTES:
        return JSONResponse({"detail": "Upload is too large"}, status_code=413)
    return await call_next(request)


app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH", "PUT"],
    allow_headers=["Content-Type", "X-Claim-Token", "X-Staff-Key", "X-Request-ID"],
    expose_headers=["X-Request-ID", "Retry-After", "Content-Disposition"],
)
app.middleware("http")(request_context)   # outermost: every response gets X-Request-ID

app.include_router(claims.router)
app.include_router(status.router)
app.include_router(staff.router)


async def _service_state(url: str, mocked: bool) -> str:
    if mocked:
        return "mock"
    if not url:
        return "not_configured"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{url}/health")
        return "ok" if r.status_code < 500 else f"error (HTTP {r.status_code})"
    except httpx.HTTPError:
        return "unreachable"


async def _database_state() -> str:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "unreachable"


@app.get("/health", tags=["meta"])
async def health(response: Response):
    """200 when the database works (Members 1/3 being down is reported, not fatal), else 503."""
    database, member1, member3 = await asyncio.gather(
        _database_state(), _service_state(settings.member1_ai_url, settings.use_mock_member1),
        _service_state(settings.member3_verify_url, settings.use_mock_member3))
    warnings = []
    if rules_are_sample():
        warnings.append("SDRF rules are a SAMPLE: relief amounts are estimates only")
    if settings.use_mock_member1:
        warnings.append("Member 1 is mocked: transcripts and fields are fake (development only)")
    if settings.use_mock_member3:
        warnings.append("Member 3 is mocked: photo checks are fake (development only)")
    response.status_code = 200 if database == "ok" else 503
    return {"ok": database == "ok", "env": settings.app_env, "database": database,
            "member1_ai": member1, "member3_verify": member3,
            "rules_version": load_sdrf_rules()["version"], "languages": SUPPORTED_LANGUAGES,
            "warnings": warnings}


@app.get("/rules/sdrf", tags=["meta"])
async def sdrf_rules():
    return load_sdrf_rules()
