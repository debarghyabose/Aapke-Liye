"""Damage vision: photo -> damage type + severity, using Claude's vision.

The key is read from VISION_API_KEY in Member-3/.env (never commit it).
If the key is missing or the API call fails, the claim is not rejected: it gets
damage type "unknown", and scoring sends it to an official for review.
"""
import base64
import io
import logging
from typing import Literal, Optional

import anthropic
from PIL import Image
from pydantic import BaseModel

from app import config
from app.schemas import DamageResult

log = logging.getLogger(__name__)

# Phone photos can be large; the API works best with images about this size.
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


class _VisionOutput(BaseModel):
    type: Literal["house", "crop", "livestock", "vehicle", "other", "none"]
    severity: float
    sdrf_category: str
    real_photo: bool
    description: str


_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.VISION_API_KEY, timeout=60.0)
    return _client


def _prepare_image(photo: bytes) -> str:
    """Shrink to MAX_SIDE_PX, convert to JPEG, return base64."""
    img = Image.open(io.BytesIO(photo))
    img = img.convert("RGB")
    img.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


def _unknown(reason: str) -> DamageResult:
    return DamageResult(type="unknown", severity=0.0, description=reason)


def assess_damage(photo: bytes) -> DamageResult:
    if not config.VISION_API_KEY:
        return _unknown("vision model not configured")

    try:
        image_b64 = _prepare_image(photo)
    except Exception:
        return _unknown("could not read image")

    try:
        response = _get_client().messages.parse(
            model=config.VISION_MODEL,
            max_tokens=2048,
            output_config={"effort": config.VISION_EFFORT},
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                    {"type": "text", "text": "Assess the damage in this claim photo."},
                ],
            }],
            output_format=_VisionOutput,
        )
    except anthropic.AuthenticationError:
        log.error("Vision API key rejected; check VISION_API_KEY in .env")
        return _unknown("vision API key invalid")
    except anthropic.RateLimitError:
        log.warning("Vision API rate limited")
        return _unknown("vision rate limited, retry later")
    except anthropic.APIStatusError as e:
        if "credit balance" in str(e.message).lower():
            log.error("Vision API: no credits left; add credits in Console > Billing")
            return _unknown("vision API credits empty")
        log.warning("Vision API error %s (request %s)", e.status_code, e.request_id)
        return _unknown("vision service error")
    except anthropic.APIConnectionError:
        log.warning("Vision API unreachable")
        return _unknown("vision service unreachable")

    if response.stop_reason == "refusal":
        return _unknown("vision model declined this image")
    out = response.parsed_output
    if out is None:
        return _unknown("vision output could not be parsed")

    return DamageResult(
        type=out.type,
        severity=max(0.0, min(1.0, out.severity)),
        description=out.description,
        sdrf_category=out.sdrf_category,
        real_photo=out.real_photo,
    )
