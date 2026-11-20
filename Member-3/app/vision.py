"""Damage vision: photo -> damage type + severity, using a vision AI model.

Pick the provider with VISION_PROVIDER in Member-3/.env:
  gemini  - Google Gemini, free tier (key: GEMINI_API_KEY from aistudio.google.com)
  claude  - Anthropic Claude, paid credits (key: VISION_API_KEY)

Keys live only in .env (never commit them). If the key is missing or the call fails,
the claim is not rejected: damage type becomes "unknown" and scoring sends the claim
to an official for review.
"""
import base64
import io
import logging
from typing import Literal, Optional

from PIL import Image
from pydantic import BaseModel, ValidationError

from app import config
from app.schemas import DamageResult

log = logging.getLogger(__name__)

# Phone photos can be large; shrink before sending to save time and quota.
MAX_SIDE_PX = 1568

SYSTEM_PROMPT = """You assess disaster damage photos for Indian government relief claims \
(SDRF norms). The disaster may be a flood, cyclone, earthquake, landslide or fire.

Look at the photo and report:
- type: the main damaged asset. One of: house, crop, livestock, vehicle, other.
  Use "none" if the photo shows no damage at all.
- severity: a number from 0.0 to 1.0.
  0.0 = no damage. 0.1-0.3 = minor (cracks, some water, small loss).
  0.4-0.6 = partial (part of the house or field destroyed or unusable).
  0.7-1.0 = severe (house collapsed or washed away, crop fully lost, animal dead).
- sdrf_category: the closest SDRF relief category, for example
  "pucca house fully damaged", "kutcha house partially damaged", "crop loss above 33%",
  "livestock loss", "hut destroyed", or "not applicable".
- real_photo: false if the image looks like a screenshot, a photo of a screen, a stock
  or news image with a watermark, a drawing, or an AI-generated image; otherwise true.
- description: one short sentence describing what is damaged, for an official to read.

Judge only what is visible. Do not guess damage you cannot see."""

USER_PROMPT = "Assess the damage in this claim photo."


class _VisionOutput(BaseModel):
    type: Literal["house", "crop", "livestock", "vehicle", "other", "none"]
    severity: float
    sdrf_category: str
    real_photo: bool
    description: str


def _prepare_image(photo: bytes) -> bytes:
    """Shrink to MAX_SIDE_PX and convert to JPEG."""
    img = Image.open(io.BytesIO(photo)).convert("RGB")
    img.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def _unknown(reason: str) -> DamageResult:
    return DamageResult(type="unknown", severity=0.0, description=reason)


def _to_result(out: _VisionOutput) -> DamageResult:
    return DamageResult(
        type=out.type,
        severity=max(0.0, min(1.0, out.severity)),
        description=out.description,
        sdrf_category=out.sdrf_category,
        real_photo=out.real_photo,
    )


# ---------------------------------------------------------------- Gemini (free tier)

_gemini_client = None


def _assess_gemini(jpeg: bytes) -> DamageResult:
    global _gemini_client
    from google import genai
    from google.genai import errors, types

    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
    try:
        response = _gemini_client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"), USER_PROMPT],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=_VisionOutput,
                temperature=0.0,
            ),
        )
    except errors.ClientError as e:
        if e.code == 429:
            log.warning("Gemini free-tier limit reached")
            return _unknown("vision daily limit reached, retry later")
        if e.code in (400, 401, 403) and "key" in str(e).lower():
            log.error("Gemini key rejected; check GEMINI_API_KEY in .env")
            return _unknown("vision API key invalid")
        log.warning("Gemini error %s: %s", e.code, str(e)[:200])
        return _unknown("vision service error")
    except errors.APIError as e:
        log.warning("Gemini server error %s", getattr(e, "code", "?"))
        return _unknown("vision service error")
    except Exception as e:  # network problems, timeouts
        log.warning("Gemini unreachable: %s", type(e).__name__)
        return _unknown("vision service unreachable")

    try:
        out = _VisionOutput.model_validate_json(response.text or "")
    except (ValidationError, ValueError):
        # Empty text usually means the safety filter blocked the image.
        return _unknown("vision output could not be parsed")
    return _to_result(out)


# ---------------------------------------------------------------- Claude (paid credits)

_client = None  # Anthropic client


def _assess_claude(jpeg: bytes) -> DamageResult:
    global _client
    import anthropic

    if _client is None:
        _client = anthropic.Anthropic(api_key=config.VISION_API_KEY, timeout=60.0)
    image_b64 = base64.standard_b64encode(jpeg).decode("utf-8")
    try:
        response = _client.messages.parse(
            model=config.VISION_MODEL,
            max_tokens=2048,
            output_config={"effort": config.VISION_EFFORT},
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                    {"type": "text", "text": USER_PROMPT},
                ],
            }],
            output_format=_VisionOutput,
        )
    except anthropic.AuthenticationError:
        log.error("Claude key rejected; check VISION_API_KEY in .env")
        return _unknown("vision API key invalid")
    except anthropic.RateLimitError:
        log.warning("Claude rate limited")
        return _unknown("vision rate limited, retry later")
    except anthropic.APIStatusError as e:
        if "credit balance" in str(e.message).lower():
            log.error("Claude: no credits left; add credits in Console > Billing")
            return _unknown("vision API credits empty")
        log.warning("Claude error %s (request %s)", e.status_code, e.request_id)
        return _unknown("vision service error")
    except anthropic.APIConnectionError:
        log.warning("Claude unreachable")
        return _unknown("vision service unreachable")

    if response.stop_reason == "refusal":
        return _unknown("vision model declined this image")
    if response.parsed_output is None:
        return _unknown("vision output could not be parsed")
    return _to_result(response.parsed_output)


# ---------------------------------------------------------------- entry point

def assess_damage(photo: bytes) -> DamageResult:
    provider = config.VISION_PROVIDER
    if provider == "gemini":
        if not config.GEMINI_API_KEY:
            return _unknown("vision model not configured")
        assess = _assess_gemini
    elif provider == "claude":
        if not config.VISION_API_KEY:
            return _unknown("vision model not configured")
        assess = _assess_claude
    else:
        return _unknown(f"unknown VISION_PROVIDER '{provider}'")

    try:
        jpeg = _prepare_image(photo)
    except Exception:
        return _unknown("could not read image")
    return assess(jpeg)
