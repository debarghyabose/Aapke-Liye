"""Damage vision: photo -> damage type + severity.

TODO(Phase 1): call the vision model chosen by the team using VISION_API_KEY.
Until then this returns "unknown" so the rest of the pipeline can be built and tested.
"""
from app import config
from app.schemas import DamageResult


def assess_damage(photo: bytes) -> DamageResult:
    if not config.VISION_API_KEY:
        return DamageResult(type="unknown", severity=0.0, description="vision model not configured")
    # Replace with the real model call. Ask it to return JSON:
    # {"type": "house|crop|livestock|vehicle|other", "severity": 0..1, "description": "..."}
    raise NotImplementedError("Wire up the vision model here")
