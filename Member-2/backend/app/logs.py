"""
Structured JSON logs, one object per line, each with the request's X-Request-ID.
Log IDs, paths, statuses and timings only: never names, phone numbers, transcripts,
addresses, tokens, keys or client IPs.
"""
import contextvars
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
_SAFE_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
_STANDARD = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {
    "message", "asctime", "color_message"}   # color_message: uvicorn's ANSI-coloured copy
log = logging.getLogger("app.request")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out = {"time": datetime.fromtimestamp(record.created, timezone.utc)
               .isoformat(timespec="milliseconds").replace("+00:00", "Z"),
               "level": record.levelname, "logger": record.name,
               "message": record.getMessage(), "request_id": request_id_var.get()}
        out.update({k: v for k, v in vars(record).items() if k not in _STANDARD})
        if record.exc_info:
            out["exception"] = self.formatException(record.exc_info)
        return json.dumps(out, default=str, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
    logging.getLogger("uvicorn.access").disabled = True   # replaced by the line below
    logging.getLogger("httpx").setLevel(logging.WARNING)  # its lines include full URLs


async def request_context(request: Request, call_next):
    """Reuse a safe incoming X-Request-ID or create one; return it and log the request."""
    incoming = request.headers.get("x-request-id", "")
    rid = incoming if _SAFE_ID.fullmatch(incoming) else uuid.uuid4().hex
    token = request_id_var.set(rid)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("unhandled error", extra={"method": request.method,
                                                "path": request.url.path})
        response = JSONResponse({"detail": "Something went wrong. Please try again.",
                                 "request_id": rid}, status_code=500)
    response.headers["X-Request-ID"] = rid
    log.info("request", extra={"method": request.method, "path": request.url.path,
                               "status": response.status_code,
                               "duration_ms": round((time.perf_counter() - start) * 1000, 1)})
    request_id_var.reset(token)
    return response
