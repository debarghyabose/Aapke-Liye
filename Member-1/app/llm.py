"""Thin wrapper around the Gemini API: one call that returns schema-valid JSON.

- JSON mode with a response schema keeps replies parseable.
- Thinking level defaults to "low": extraction is short and latency matters
  for a voice turn. Set LLM_THINKING_LEVEL="" for models that don't support it.
- Callers pass content as a string, or a list of blocks:
    {"type": "text", "text": "..."}
    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "..."}}
    {"type": "audio", "source": {"type": "base64", "media_type": "audio/wav", "data": "..."}}
"""
from __future__ import annotations

import base64
import json
import logging
import os
import time
from typing import Any

from google import genai
from google.genai import errors, types

from .config import Settings

log = logging.getLogger("aapke_liye.llm")

_client: genai.Client | None = None


class LLMError(RuntimeError):
    pass


def client() -> genai.Client:
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise LLMError("GEMINI_API_KEY is not set in .env")
        timeout_ms = int(float(os.getenv("LLM_TIMEOUT_S", "15")) * 1000)
        _client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=timeout_ms))
    return _client


def _parts(content: str | list[dict[str, Any]]) -> list[types.Part]:
    if isinstance(content, str):
        return [types.Part.from_text(text=content)]
    parts = []
    for block in content:
        if block["type"] == "text":
            parts.append(types.Part.from_text(text=block["text"]))
        elif block["type"] in ("image", "audio"):
            src = block["source"]
            parts.append(types.Part.from_bytes(data=base64.b64decode(src["data"]), mime_type=src["media_type"]))
    return parts


def structured(
    settings: Settings,
    *,
    system: str,
    content: str | list[dict[str, Any]],
    schema: dict[str, Any],
    max_tokens: int = 4000,
) -> dict[str, Any]:
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        response_json_schema=schema,
        max_output_tokens=max_tokens,
    )
    if settings.llm_thinking_level:
        config.thinking_config = types.ThinkingConfig(thinking_level=settings.llm_thinking_level)

    gem = client()  # raises LLMError if the key is missing
    models = [settings.llm_model]
    for fb in settings.llm_fallback_model.split(","):  # comma-separated, tried in order
        fb = fb.strip()
        if fb and fb not in models:
            models.append(fb)

    # After every model has failed once, pause briefly and give the main model one more try.
    attempts = models + models[:1]
    resp = None
    for i, model in enumerate(attempts):
        last = i == len(attempts) - 1
        if i == len(models):
            log.warning("all Gemini models busy; retrying %s in 1.5 s", model)
            time.sleep(1.5)
        try:
            resp = gem.models.generate_content(
                model=model,
                contents=[types.Content(role="user", parts=_parts(content))],
                config=config,
            )
            break
        except errors.ClientError as exc:  # 4xx: bad key, bad model name, quota, bad request
            if exc.code == 429 and not last:
                log.warning("%s rate-limited; trying %s", model, attempts[i + 1])
                continue
            if exc.code == 429:
                raise LLMError("Gemini rate limit or quota hit; retry shortly") from exc
            raise LLMError(f"Gemini request error {exc.code}: {exc.message}") from exc
        except errors.ServerError as exc:  # 5xx: usually "model overloaded"
            if not last:
                log.warning("%s unavailable (%s); trying %s", model, exc.code, attempts[i + 1])
                continue
            raise LLMError(f"Gemini server error {exc.code}; retry shortly") from exc
        except errors.APIError as exc:
            raise LLMError(f"Gemini API error: {exc}") from exc
        except Exception as exc:  # timeouts and network problems
            if not last:
                log.warning("%s did not answer (%s); trying %s", model, type(exc).__name__, attempts[i + 1])
                continue
            raise LLMError(f"could not reach Gemini: {exc}") from exc

    cand = (resp.candidates or [None])[0]
    reason = getattr(cand, "finish_reason", None)
    reason = getattr(reason, "name", str(reason)) if reason else None
    if reason == "MAX_TOKENS":
        raise LLMError("Gemini reply was cut off (max_output_tokens)")
    if reason in {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "RECITATION"}:
        raise LLMError(f"Gemini blocked the reply ({reason})")

    text = resp.text
    if not text:
        raise LLMError(f"Gemini returned no text (finish_reason={reason})")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError("Gemini returned invalid JSON") from exc


# ---------- JSON-schema helpers (every key required, so the model always returns it) ----------


def nullable(t: str, **extra) -> dict[str, Any]:
    return {"type": [t, "null"], **extra}


def obj(props: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}
