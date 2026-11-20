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

# SQLite file with every photo check (dashboard data + duplicate fingerprints).
DB_PATH = os.getenv("MEMBER3_DB_PATH", "member3.db")
# If set, /dashboard/* requires the header X-Dashboard-Key with this value.
# Leave empty only on your own computer: the dashboard shows exact victim locations.
DASHBOARD_API_KEY = os.getenv("DASHBOARD_API_KEY", "")
# Web pages allowed to read /dashboard from a browser (Member 5's dashboard).
# "null" = the dashboard opened straight from a file (file://). Remove it in production.
DASHBOARD_CORS_ORIGINS = [o.strip() for o in os.getenv(
    "DASHBOARD_CORS_ORIGINS",
    "null,http://localhost:5500,http://127.0.0.1:5500,http://localhost:8080,http://localhost:3000",
).split(",") if o.strip()]

# Photos whose perceptual hashes differ by this many bits or fewer count as the same photo.
PHASH_MAX_DISTANCE = 8
# Two claims from the same phone this close together (metres) count as the same claim.
SAME_CLAIM_RADIUS_M = 50

# --- Advanced fraud checks (all are review flags for an official, never automatic rejection)
# Photos from different claims taken within this many metres may show the same house.
# Phone GPS is often only accurate to 5-20 m, so neighbours can also be flagged.
SAME_HOUSE_RADIUS_M = float(os.getenv("SAME_HOUSE_RADIUS_M", "25"))
# More than this many *other* claims from one phone in 24 h is flagged (Member 5's spec:
# "> 3 claims ... within 24 hours"). NGO workers filing for many families will trip it too.
PHONE_MAX_OTHER_CLAIMS_24H = int(os.getenv("PHONE_MAX_OTHER_CLAIMS_24H", "3"))
# Secret for phone fingerprints. Set a long random value in production.
PHONE_HASH_KEY = os.getenv("PHONE_HASH_KEY", "")
