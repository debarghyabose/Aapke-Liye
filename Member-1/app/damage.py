"""Phase 2: score damage by comparing a normal-time baseline photo with a damage photo."""
from __future__ import annotations

import base64
import io

from . import llm
from .config import Settings
from .schemas import DamageCompareRequest, DamageCompareResponse

LEVEL_BANDS = [(10, "none"), (40, "partial"), (75, "severe"), (101, "destroyed")]
ALLOWED_MEDIA = {"image/jpeg", "image/png", "image/webp", "image/gif"}

_SCHEMA = llm.obj({
    "same_property": {"type": "boolean"},
    "damage_score": {"type": "integer", "description": "0 = no visible damage, 100 = completely destroyed"},
    "damaged_items": {"type": "array", "items": {"type": "string"}},
    "reason": {"type": "string"},
    "confidence": {"type": "number"},
})

_SYSTEM = """You assess disaster damage for relief claims in India.
Image 1 is the property in normal times (baseline). Image 2 is after the disaster.
1. Decide whether both photos show the same property (same building, field or vehicle).
2. Score visible damage in image 2 compared with image 1, from 0 to 100, with this rubric:
   0-10 no visible damage; 11-40 partial (cracks, some roof sheets, part of field flooded);
   41-75 severe (walls broken, most of roof gone, most of crop flattened);
   76-100 destroyed (collapsed, washed away, crop fully lost).
3. List the damaged items you can actually see (e.g. "tin roof", "front wall", "paddy field").
Only describe what is visible. If the photos are unclear, say so and lower your confidence."""


def level_for(score: int) -> str:
    for upper, name in LEVEL_BANDS:
        if score < upper:
            return name
    return "destroyed"


def _finalize(same: bool, score: int, items: list[str], reason: str, conf: float) -> DamageCompareResponse:
    score = max(0, min(100, int(score)))
    conf = max(0.0, min(1.0, float(conf)))
    return DamageCompareResponse(
        same_property=same, damage_score=score, level=level_for(score), damaged_items=items,
        reason=reason, confidence=round(conf, 2),
        needs_human_review=(not same) or conf < 0.5,
    )


def _mock(req: DamageCompareRequest) -> DamageCompareResponse:
    """Pixel difference stand-in so Member 2 can integrate without API keys."""
    try:
        from PIL import Image, ImageChops, ImageStat

        a = Image.open(io.BytesIO(base64.b64decode(req.baseline_image_base64))).convert("L").resize((128, 128))
        b = Image.open(io.BytesIO(base64.b64decode(req.damage_image_base64))).convert("L").resize((128, 128))
        diff = ImageStat.Stat(ImageChops.difference(a, b)).mean[0]  # 0..255
        score = int(min(100, diff / 255 * 250))
        return _finalize(True, score, [], f"mock: mean pixel difference {diff:.1f}", 0.3)
    except Exception as exc:  # noqa: BLE001
        return _finalize(False, 0, [], f"mock: could not read images ({exc})", 0.0)


def compare(req: DamageCompareRequest, settings: Settings) -> DamageCompareResponse:
    for mt in (req.baseline_media_type, req.damage_media_type):
        if mt not in ALLOWED_MEDIA:
            raise ValueError(f"unsupported image type {mt}; use one of {sorted(ALLOWED_MEDIA)}")
    if settings.is_mock:
        return _mock(req)
    content = [
        {"type": "text", "text": "Image 1 (baseline, normal times):"},
        {"type": "image", "source": {"type": "base64", "media_type": req.baseline_media_type,
                                     "data": req.baseline_image_base64}},
        {"type": "text", "text": "Image 2 (after the disaster):"},
        {"type": "image", "source": {"type": "base64", "media_type": req.damage_media_type,
                                     "data": req.damage_image_base64}},
        {"type": "text", "text": f"Context from the claim: {req.context or 'none'}"},
    ]
    out = llm.structured(settings, system=_SYSTEM, content=content, schema=_SCHEMA, max_tokens=2000)
    return _finalize(out["same_property"], out["damage_score"], out["damaged_items"], out["reason"],
                     out["confidence"])
