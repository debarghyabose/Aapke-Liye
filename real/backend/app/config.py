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
# Vercel functions only have a writable /tmp (ephemeral; use Cloudinary for durable images there)
_DEFAULT_STORAGE = Path("/tmp/storage") if os.getenv("VERCEL") else BASE_DIR / "storage"
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", _DEFAULT_STORAGE))
if os.getenv("VERCEL") and not str(STORAGE_DIR).startswith("/tmp"):
    STORAGE_DIR = _DEFAULT_STORAGE  # only /tmp is writable on Vercel
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
# Base64 DER (PKCS#8) RSA key and base64 raw Ed25519 key. Unset -> ephemeral keys (dev only).
MESH_PRIVATE_KEY = os.getenv("MESH_PRIVATE_KEY", "")
MESH_RECEIPT_KEY = os.getenv("MESH_RECEIPT_KEY", "")

PORT = int(os.getenv("PORT", 8080))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
