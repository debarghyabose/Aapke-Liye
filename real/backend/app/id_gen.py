"""
Proper ID Generation and Secure Bearer Token Management for Aapke Liye
"""
import hashlib
import secrets
import random
from typing import Optional

STATE_CODES = {
    "west_bengal": "WB",
    "west bengal": "WB",
    "odisha": "OD",
    "orissa": "OD",
    "bihar": "BR",
    "assam": "AS",
    "maharashtra": "MH",
    "tamil_nadu": "TN",
    "tamil nadu": "TN",
    "telangana": "TS",
    "andhra_pradesh": "AP",
    "andhra pradesh": "AP",
    "kerala": "KL",
    "karnataka": "KA",
    "uttar_pradesh": "UP",
    "uttar pradesh": "UP",
    "uttarakhand": "UK",
}

def generate_claim_id(state: Optional[str] = None) -> str:
    """Generates globally unique official disaster relief claim ID: AL-2026-{STATE}-{UNIQUE_CODE}."""
    st = "IN"
    if state:
        st = STATE_CODES.get(str(state).strip().lower(), "IN")
    random_part = secrets.token_hex(4).upper()
    return f"AL-2026-{st}-{random_part}"

def generate_household_id() -> str:
    """Generates globally unique household document vault ID: HH-2026-{UNIQUE_CODE}."""
    random_part = secrets.token_hex(4).upper()
    return f"HH-2026-{random_part}"

def new_token() -> str:
    """Generates a cryptographically strong 256-bit bearer token."""
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    """Returns SHA-256 hash of the bearer token."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()

def verify_token(token: str, token_hash: str) -> bool:
    """Constant-time token hash verification."""
    if not token or not token_hash:
        return False
    return secrets.compare_digest(hash_token(token), token_hash)
