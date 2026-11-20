"""All settings come from environment variables (or a .env file)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

try:  # optional: load .env if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# SQLite by default so it runs with zero setup; switch to Postgres with:
# DATABASE_URL=postgresql+psycopg://aapke:aapke@localhost:5432/aapke_liye
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'aapke_liye.db'}")

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BASE_DIR / "storage"))
RULES_DIR = BASE_DIR / "rules"

# Teammates' services. Leave empty to use the built-in mock responses.
MEMBER1_AI_URL = os.getenv("MEMBER1_AI_URL", "")          # e.g. http://localhost:8001
MEMBER3_VERIFY_URL = os.getenv("MEMBER3_VERIFY_URL", "")  # e.g. http://localhost:8002

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

SUPPORTED_LANGUAGES = ["en", "hi", "bn", "te", "mr", "ta"]  # English + top 5

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
