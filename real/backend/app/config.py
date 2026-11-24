"""
Aapke Liye - Standalone Backend Configuration
Connects to Firebase Firestore on Google Cloud project: trusty-obelisk-515402-p3
"""
import os
from pathlib import Path
from typing import List, Dict

try:  # load backend/.env for local runs (optional dependency)
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BASE_DIR / "storage"))
RULES_DIR = BASE_DIR / "rules"
TEMPLATES_DIR = BASE_DIR / "templates"
FONTS_DIR = BASE_DIR / "fonts"
COPERNICUS_DIR = BASE_DIR / "data" / "copernicus"

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("PROJECT_ID", "trusty-obelisk-515402-p3"))
PROJECT_NUMBER = os.getenv("PROJECT_NUMBER", "881624105738")
PROJECT_NAME = "aapke liye"

# Gemini AI API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODELS = [
    m.strip() for m in os.getenv("GEMINI_MODELS", "gemini-3.5-flash-lite,gemini-3.5-flash,gemini-3.8-flash").split(",")
]

# Supported regional languages
SUPPORTED_LANGUAGES = ["en", "hi", "bn", "mr", "ta", "te"]

# Staff Authorization Keys for Officials Dashboard
# Format: STAFF_API_KEYS="name1:key1,name2:key2"
STAFF_API_KEYS: Dict[str, str] = {
    name.strip(): key.strip()
    for name, _, key in (
        pair.partition(":") for pair in os.getenv("STAFF_API_KEYS", "").split(",") if ":" in pair
    )
}
DASHBOARD_API_KEY = os.getenv("DASHBOARD_API_KEY", "")

# Cloudinary image store config
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")

# Mesh relay cryptographic keys
MESH_PRIVATE_KEY = os.getenv("MESH_PRIVATE_KEY", """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""")
MESH_RECEIPT_KEY = os.getenv("MESH_RECEIPT_KEY", "fykonAlAtQddz44u5BQ0fNUL9p9gWOrr2zQ/UOww4Rs=")

PORT = int(os.getenv("PORT", 8080))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
