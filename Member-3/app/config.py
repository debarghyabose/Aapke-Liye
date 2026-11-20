"""Settings read from .env (see .env.example)."""
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

ZONE_LAT = float(os.getenv("DISASTER_ZONE_LAT", "22.5726"))
ZONE_LON = float(os.getenv("DISASTER_ZONE_LON", "88.3639"))
ZONE_RADIUS_KM = float(os.getenv("DISASTER_ZONE_RADIUS_KM", "50"))
DISASTER_START = datetime.fromisoformat(os.getenv("DISASTER_START_DATE", "2026-11-01"))

VISION_PROVIDER = os.getenv("VISION_PROVIDER", "gemini").strip().lower()  # gemini | claude

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Tried in order; a busy (503), rate-limited (429) or slow model falls through to the next.
GEMINI_MODELS = [m.strip() for m in os.getenv(
    "GEMINI_MODELS", os.getenv("GEMINI_MODEL", "gemini-3.6-flash,gemini-3.5-flash-lite")).split(",") if m.strip()]
GEMINI_MODEL = GEMINI_MODELS[0]
# Whole damage check must finish inside Member 2's 30 s timeout.
VISION_DEADLINE_SECONDS = float(os.getenv("VISION_DEADLINE_SECONDS", "25"))
# Max time for each model except the last, so a slow model can't use up the whole budget.
VISION_PER_MODEL_SECONDS = float(os.getenv("VISION_PER_MODEL_SECONDS", "12"))

VISION_API_KEY = os.getenv("VISION_API_KEY", "")  # Anthropic key, for VISION_PROVIDER=claude
VISION_MODEL = os.getenv("VISION_MODEL", "claude-opus-5-5")
VISION_EFFORT = os.getenv("VISION_EFFORT", "medium")  # low | medium | high

# Photos whose perceptual hashes differ by this many bits or fewer count as the same photo.
PHASH_MAX_DISTANCE = 8
# Two claims from the same phone this close together (metres) count as the same claim.
SAME_CLAIM_RADIUS_M = 50
