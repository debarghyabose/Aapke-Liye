"""Mesh "lite": a sealed claim handed from phone to phone, filed when any phone has signal.

Phone A (no network) seals its claim with this service's public key (offline-client/mesh.js)
and shows it as a QR code or a file. Phone B carries it and, once online, posts it here.
Only this service can open it; any change to it on the way makes it fail to open.

    GET  /mesh/public-key           key + limits, cached by the app while online
    POST /mesh/envelopes            a carried envelope -> claim filed through Member 2
    GET  /mesh/receipts/{claim_id}  signed "your claim reached the relief office" receipt

Envelope (JSON):
    {"v": 1, "claim_id": "<uuid made on phone A>", "created_at": "2026-11-21T08:00:00Z",
     "priority": "urgent" | "normal", "alg": "RSA-OAEP-256+A256GCM",
     "key": b64(RSA-OAEP-SHA256(aes_key)), "iv": b64(12 bytes), "ct": b64(AES-256-GCM ciphertext)}
The header (v|claim_id|created_at|priority) is the GCM additional data, so it cannot be altered.

Sealed payload (JSON):
    {"consent": true, "consent_text_version": "v1", "language": "bn", "fields": {...},
     "audio": {"data": b64, "content_type": "audio/webm"},
     "photos": [{"data": b64, "content_type": "image/jpeg", "lat": .., "lon": .., "taken_at": ".."}],
     "submit": true}
Everything except consent is optional. Limits come from Member-5/rules/mesh_policy.json.

Keys: python scripts/make_mesh_keys.py writes MESH_PRIVATE_KEY and MESH_RECEIPT_KEY to .env.
"""
import base64
import binascii
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import APIRouter, HTTPException, Request

from app import config
from app.store import get_store
from app.whatsapp import Member2, Member2Error

log = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/mesh", tags=["mesh"])

ALG = "RSA-OAEP-256+A256GCM"
CLOCK_SKEW = timedelta(minutes=10)      # phones' clocks are often a little off
CLAIM_ID = re.compile(r"^[0-9a-fA-F-]{16,64}$")
DEFAULT_POLICY = {"version": "default", "storage": {"max_payload_bytes": 1572864, "ttl_seconds": 604800},
                  "security": {"allowed_priority_flags": ["urgent", "normal"]},
                  "receipts": {"confirmation_text": "Your claim reached the relief office"}}


class EnvelopeError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


# ------------------------------------------------------------------ keys and policy

@lru_cache(maxsize=1)
def policy() -> dict:
    try:
        return json.loads(Path(config.MESH_POLICY_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        log.warning("Mesh policy %s not found: using defaults", config.MESH_POLICY_FILE)
        return DEFAULT_POLICY


def max_payload() -> int:
    return int(policy()["storage"]["max_payload_bytes"])


def ttl() -> timedelta:
    return timedelta(seconds=int(policy()["storage"]["ttl_seconds"]))


def priorities() -> set:
    return set(policy()["security"]["allowed_priority_flags"])


def enabled() -> bool:
    return bool(config.MESH_PRIVATE_KEY and config.MESH_RECEIPT_KEY)


@lru_cache(maxsize=4)
def _private_key(b64: str) -> rsa.RSAPrivateKey:
    return serialization.load_der_private_key(base64.b64decode(b64), password=None)


@lru_cache(maxsize=4)
def _receipt_key(b64: str) -> ed25519.Ed25519PrivateKey:
    return ed25519.Ed25519PrivateKey.from_private_bytes(base64.b64decode(b64))


def new_keys() -> tuple[str, str]:
    """(MESH_PRIVATE_KEY, MESH_RECEIPT_KEY) values for .env."""
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    der = rsa_key.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
    ed = ed25519.Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    return base64.b64encode(der).decode(), base64.b64encode(ed).decode()


def public_info() -> dict:
    pub = _private_key(config.MESH_PRIVATE_KEY).public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    receipt_pub = _receipt_key(config.MESH_RECEIPT_KEY).public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {"alg": ALG, "public_key_spki": base64.b64encode(pub).decode(),
            "receipt_alg": "Ed25519", "receipt_public_key": base64.b64encode(receipt_pub).decode(),
            "max_payload_bytes": max_payload(), "ttl_seconds": int(ttl().total_seconds()),
            "priorities": sorted(priorities()), "policy_version": policy().get("version")}


# ------------------------------------------------------------------ envelopes

def header_bytes(env: dict) -> bytes:
    """The unencrypted header, bound to the ciphertext as AES-GCM additional data."""
    return f"{env['v']}|{env['claim_id']}|{env['created_at']}|{env['priority']}".encode()


def _b64(value, what: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, TypeError, ValueError):
        raise EnvelopeError(400, f"{what} is not valid base64") from None


def _parse_time(value: str) -> datetime:
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise EnvelopeError(400, "created_at must be an ISO 8601 time") from None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def check_header(env: dict, now: Optional[datetime] = None) -> None:
    """Cheap checks done before decrypting anything."""
    if not isinstance(env, dict) or env.get("v") != 1 or env.get("alg") != ALG:
        raise EnvelopeError(400, f"Not a version 1 {ALG} envelope")
    for k in ("claim_id", "created_at", "priority", "key", "iv", "ct"):
        if not isinstance(env.get(k), str):
            raise EnvelopeError(400, f"Envelope field {k} is missing")
    if not CLAIM_ID.match(env["claim_id"]):
        raise EnvelopeError(400, "claim_id must be a UUID")
    if env["priority"] not in priorities():
        raise EnvelopeError(400, f"priority must be one of {sorted(priorities())}")
    now = now or datetime.now(timezone.utc)
    created = _parse_time(env["created_at"])
    if created > now + CLOCK_SKEW:
        raise EnvelopeError(400, "created_at is in the future")
    if now - created > ttl():
        raise EnvelopeError(410, "Envelope expired (older than the mesh time-to-live)")
    # base64 is 4/3 of the bytes: refuse oversized envelopes before decoding them
    if len(env["ct"]) * 3 // 4 > max_payload() + 16:
        raise EnvelopeError(413, f"Payload larger than {max_payload()} bytes")


def open_envelope(env: dict) -> dict:
    """Decrypt and return the payload. Any tampering fails here."""
    key = _private_key(config.MESH_PRIVATE_KEY)
    try:
        aes_key = key.decrypt(_b64(env["key"], "key"), padding.OAEP(
            mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
        plain = AESGCM(aes_key).decrypt(_b64(env["iv"], "iv"), _b64(env["ct"], "ct"), header_bytes(env))
    except (ValueError, InvalidTag):
        raise EnvelopeError(400, "Envelope was changed on the way, or was not sealed for this server") from None
    if len(plain) > max_payload():
        raise EnvelopeError(413, f"Payload larger than {max_payload()} bytes")
    try:
        payload = json.loads(plain)
    except ValueError:
        raise EnvelopeError(400, "Sealed payload is not JSON") from None
    if not isinstance(payload, dict) or payload.get("consent") is not True:
        raise EnvelopeError(422, "The claimant's consent is missing from the sealed claim")
    return payload


def seal(payload: dict, public_spki_b64: str, claim_id: str, priority: str = "normal",
         created_at: Optional[str] = None) -> dict:
    """Python version of offline-client/mesh.js sealClaim (for tests and scripts)."""
    import os
    pub = serialization.load_der_public_key(base64.b64decode(public_spki_b64))
    env = {"v": 1, "claim_id": claim_id, "priority": priority, "alg": ALG,
           "created_at": created_at or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")}
    aes_key, iv = AESGCM.generate_key(bit_length=256), os.urandom(12)
    ct = AESGCM(aes_key).encrypt(iv, json.dumps(payload).encode(), header_bytes(env))
    wrapped = pub.encrypt(aes_key, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    return {**env, "key": base64.b64encode(wrapped).decode(), "iv": base64.b64encode(iv).decode(),
            "ct": base64.b64encode(ct).decode()}


# ------------------------------------------------------------------ receipts

def make_receipt(claim_id: str, received_at: str, reference: Optional[str]) -> dict:
    signed = f"{claim_id}|{received_at}".encode()
    sig = _receipt_key(config.MESH_RECEIPT_KEY).sign(signed)
    return {"claim_id": claim_id, "received_at": received_at, "reference": reference,
            "message": policy()["receipts"]["confirmation_text"],
            "signed": signed.decode(), "signature": base64.b64encode(sig).decode()}


def verify_receipt(receipt: dict, receipt_public_key_b64: str) -> bool:
    pub = ed25519.Ed25519PublicKey.from_public_bytes(base64.b64decode(receipt_public_key_b64))
    try:
        pub.verify(base64.b64decode(receipt["signature"]), f"{receipt['claim_id']}|{receipt['received_at']}".encode())
        return True
    except (InvalidSignature, KeyError, ValueError):
        return False


# ------------------------------------------------------------------ filing the claim

async def file_claim(m2: Member2, payload: dict) -> tuple[str, str]:
    """Create the claim in Member 2 like the app does. Returns (Member 2 claim id, state)."""
    c = await m2.create_claim(payload.get("language") or "en",
                              consent_text_version=str(payload.get("consent_text_version") or "mesh-v1"))
    cid, token = c["id"], c["claim_token"]
    fields = payload.get("fields") or {}
    if isinstance(fields, dict) and fields:
        try:
            await m2.update_fields(cid, token, fields)
        except Member2Error as e:
            if e.status != 422:
                raise
            for k, v in fields.items():             # keep the fields that are valid
                try:
                    await m2.update_fields(cid, token, {k: v})
                except Member2Error as e2:
                    if e2.status != 422:
                        raise
    audio = payload.get("audio")
    if isinstance(audio, dict) and audio.get("data"):
        try:
            await m2.upload_audio(cid, token, _b64(audio["data"], "audio"), audio.get("content_type") or "audio/webm")
        except Member2Error as e:
            if e.status != 503:                      # 503: Member 2 keeps it and retries later
                log.info("Mesh: audio for %s not accepted: %s", cid, e)
    for p in (payload.get("photos") or [])[:10]:
        if not isinstance(p, dict) or not p.get("data"):
            continue
        try:
            await m2.upload_photo(cid, token, _b64(p["data"], "photo"), p.get("content_type") or "image/jpeg",
                                  p.get("lat"), p.get("lon"), p.get("taken_at"))
        except Member2Error as e:
            if e.status >= 500:
                raise
            log.info("Mesh: photo for %s not accepted: %s", cid, e)
    state = "draft"
    if payload.get("submit"):
        try:
            await m2.submit(cid, token)
            state = "submitted"
        except Member2Error as e:
            if e.status != 422:
                raise
            state = "draft_missing_details"
    return cid, state


# ------------------------------------------------------------------ HTTP

def _require_enabled():
    if not enabled():
        raise HTTPException(503, "Mesh is not set up on this server (run scripts/make_mesh_keys.py)")


_member2: Optional[Member2] = None
_inflight: set[str] = set()      # envelopes being filed now (two carriers at the same moment)


def get_member2() -> Member2:
    global _member2
    if _member2 is None:
        _member2 = Member2(config.MEMBER2_API_URL)
    return _member2


def set_member2(m2: Optional[Member2]) -> None:
    """For tests."""
    global _member2
    _member2 = m2


@router.get("/public-key")
def public_key() -> dict:
    _require_enabled()
    return public_info()


@router.post("/envelopes")
async def receive_envelope(request: Request) -> dict:
    _require_enabled()
    raw = await request.body()
    if len(raw) > max_payload() * 4 // 3 + 64 * 1024:
        raise HTTPException(413, f"Envelope larger than the {max_payload()} byte limit")
    try:
        env = json.loads(raw)
    except ValueError:
        raise HTTPException(400, "Body must be the envelope JSON") from None
    store = get_store()
    try:
        check_header(env)
        if env["claim_id"] in _inflight:
            raise EnvelopeError(409, "This envelope is being delivered right now: try again in a minute")
        done = store.mesh_get(env["claim_id"])
        if done:                                   # carried twice: same receipt, no second claim
            return {"status": "duplicate", "receipt": make_receipt(env["claim_id"], done["received_at"],
                                                                   done["reference"])}
        payload = open_envelope(env)
    except EnvelopeError as e:
        raise HTTPException(e.status, str(e)) from None
    _inflight.add(env["claim_id"])
    try:
        reference, state = await file_claim(get_member2(), payload)
    except Member2Error as e:
        log.warning("Mesh: Member 2 could not take claim %s: %s", env["claim_id"], e)
        raise HTTPException(503, "The relief server is not reachable right now: keep the envelope and try again",
                            headers={"Retry-After": "60"}) from None
    finally:
        _inflight.discard(env["claim_id"])
    received_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    if not store.mesh_record(env["claim_id"], reference, received_at, env["priority"], state):
        done = store.mesh_get(env["claim_id"])     # another carrier delivered it at the same moment
        return {"status": "duplicate", "receipt": make_receipt(env["claim_id"], done["received_at"], done["reference"])}
    log.info("Mesh: envelope %s delivered as claim %s (%s)", env["claim_id"], reference, state)
    return {"status": state, "receipt": make_receipt(env["claim_id"], received_at, reference)}


@router.get("/receipts/{claim_id}")
def receipt(claim_id: str) -> dict:
    _require_enabled()
    done = get_store().mesh_get(claim_id)
    if not done:
        raise HTTPException(404, "Not delivered yet")
    return make_receipt(claim_id, done["received_at"], done["reference"])
